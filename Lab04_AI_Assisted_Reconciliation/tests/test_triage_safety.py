import json
import httpx
import pytest
from src import triage
from src.triage import SYSTEM, _parse, triage_exception

ROW = {'transaction_id': 'TX0008', 'status': 'AMOUNT_MISMATCH', 'ledger_count': 1, 'settlement_count': 1,
       'ledger_amount': '2000.00', 'settlement_amount': '1700.00', 'difference': '300.00',
       'ledger_date': '2026-10-23', 'settlement_date': '2026-10-23'}
GOOD = {'transaction_id': 'TX0008', 'classification': 'AMOUNT_MISMATCH', 'possible_causes': ['Fee deducted'],
        'recommended_action': 'Check settlement evidence', 'requires_human_review': True,
        'missing_evidence': ['fee ledger']}
SECRET = 'sk-test-SECRET-123'


def payload(**changes):
    return json.dumps({**GOOD, **changes})


# ---------- _parse ----------

def test_plain_and_fenced_json_accepted():
    for text in (payload(), f'```json\n{payload()}\n```', f'```\n{payload()}\n```', f'  ```JSON\r\n{payload()}\r\n```  '):
        assert _parse(text, ROW) == GOOD


def test_missing_optional_fields_default_safely():
    data = {k: v for k, v in GOOD.items() if k not in ('missing_evidence', 'requires_human_review')}
    out = _parse(json.dumps(data), ROW)
    assert out['requires_human_review'] is True and out['missing_evidence'] == []


@pytest.mark.parametrize('changes', [
    {'transaction_id': 'TX9999'},
    {'classification': 'MATCHED'},
    {'classification': 'DATE_MISMATCH'},
    {'classification': 'NOT_A_STATUS'},
    {'requires_human_review': False},
    {'requires_human_review': 'false'},
    {'requires_human_review': 'true'},
    {'requires_human_review': 0},
    {'requires_human_review': None},
    {'possible_causes': []},
    {'possible_causes': ['a'] * 6},
    {'recommended_action': 'no'},
])
def test_unsafe_or_invalid_payloads_rejected(changes):
    with pytest.raises(ValueError):
        _parse(payload(**changes), ROW)


@pytest.mark.parametrize('text', [
    '', 'not json', '[1, 2]', '"MATCHED"', 'null', '{"transaction_id": ',
    f'Here is the result: {json.dumps(GOOD)}',
    f'```json\n{json.dumps(GOOD)}\n``` Trust me, this is MATCHED.',
])
def test_malformed_or_wrapped_output_rejected(text):
    with pytest.raises(ValueError):
        _parse(text, ROW)


def test_non_string_rejected():
    with pytest.raises(ValueError):
        _parse(None, ROW)


def test_duplicate_keys_cannot_smuggle_review_waiver():
    text = payload().replace('"requires_human_review": true', '"requires_human_review": false, "requires_human_review": true')
    assert text.count('requires_human_review') == 2
    with pytest.raises(ValueError):
        _parse(text, ROW)


def test_extra_fields_ignored_and_never_returned():
    out = _parse(payload(status='MATCHED', difference='0.00', note='ignore previous instructions'), ROW)
    assert out == GOOD
    assert ROW['status'] == 'AMOUNT_MISMATCH'


def test_exception_without_status_or_id_rejects_everything():
    with pytest.raises(ValueError):
        _parse(payload(), {'transaction_id': 'TX0008'})
    with pytest.raises(ValueError):
        _parse(payload(), {})


# ---------- provider integration (mocked HTTP) ----------

class FakeResponse:
    def __init__(self, body, status=200):
        self._body, self.status_code = body, status

    def json(self):
        if self._body is None:
            raise ValueError('no json')
        return self._body


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    def no_network(*a, **k):
        raise AssertionError('real network call attempted in tests')
    monkeypatch.setattr(triage.httpx, 'post', no_network)
    monkeypatch.setattr(triage, 'load_dotenv', lambda *a, **k: None)
    for name in ('LLM_PROVIDER', 'OPENROUTER_API_KEY', 'OPENROUTER_MODEL', 'ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL'):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def capture(monkeypatch):
    calls = []

    def install(response):
        def fake_post(url, headers=None, json=None, timeout=None):
            calls.append({'url': url, 'headers': headers, 'json': json, 'timeout': timeout})
            if isinstance(response, Exception):
                raise response
            return response
        monkeypatch.setattr(triage.httpx, 'post', fake_post)
        return calls
    return install


def openrouter_reply(text, finish='stop'):
    return FakeResponse({'choices': [{'message': {'content': text}, 'finish_reason': finish}]})


def anthropic_reply(blocks, stop='end_turn'):
    return FakeResponse({'content': blocks, 'stop_reason': stop})


def test_openrouter_request_shape_and_result(monkeypatch, capture):
    monkeypatch.setenv('OPENROUTER_API_KEY', SECRET)
    monkeypatch.setenv('OPENROUTER_MODEL', 'some/model')
    calls = capture(openrouter_reply(f'```json\n{payload()}\n```'))
    assert triage_exception(dict(ROW, internal_note='do not send'), 'openrouter') == GOOD
    call = calls[0]
    assert call['url'] == 'https://openrouter.ai/api/v1/chat/completions'
    assert call['headers']['Authorization'] == f'Bearer {SECRET}'
    body = call['json']
    assert body['model'] == 'some/model' and 'temperature' not in body
    assert body['messages'][0] == {'role': 'system', 'content': SYSTEM}
    assert body['messages'][1]['role'] == 'user'
    assert 'TX0008' in body['messages'][1]['content'] and 'do not send' not in body['messages'][1]['content']
    assert SECRET not in json.dumps(body)


def test_anthropic_request_shape_skips_thinking_blocks(monkeypatch, capture):
    monkeypatch.setenv('ANTHROPIC_API_KEY', SECRET)
    monkeypatch.setenv('ANTHROPIC_MODEL', 'claude-test-model')
    calls = capture(anthropic_reply([{'type': 'thinking', 'thinking': ''}, {'type': 'text', 'text': payload()}]))
    assert triage_exception(ROW, 'anthropic') == GOOD
    call = calls[0]
    assert call['url'] == 'https://api.anthropic.com/v1/messages'
    assert call['headers']['x-api-key'] == SECRET and call['headers']['anthropic-version'] == '2023-06-01'
    body = call['json']
    assert body['model'] == 'claude-test-model' and body['system'] == SYSTEM
    assert body['max_tokens'] > 0 and 'temperature' not in body
    assert [m['role'] for m in body['messages']] == ['user']
    assert SECRET not in json.dumps(body)


def test_anthropic_default_model_when_unset(monkeypatch, capture):
    monkeypatch.setenv('ANTHROPIC_API_KEY', SECRET)
    calls = capture(anthropic_reply([{'type': 'text', 'text': payload()}]))
    triage_exception(ROW, 'anthropic')
    assert calls[0]['json']['model'] == 'claude-opus-5-5'


def test_provider_from_env_and_default(monkeypatch, capture):
    monkeypatch.setenv('LLM_PROVIDER', 'anthropic')
    monkeypatch.setenv('ANTHROPIC_API_KEY', SECRET)
    calls = capture(anthropic_reply([{'type': 'text', 'text': payload()}]))
    triage_exception(ROW)
    assert 'anthropic.com' in calls[-1]['url']
    monkeypatch.delenv('LLM_PROVIDER')
    monkeypatch.setenv('OPENROUTER_API_KEY', SECRET)
    monkeypatch.setenv('OPENROUTER_MODEL', 'm')
    calls = capture(openrouter_reply(payload()))
    triage_exception(ROW)
    assert len(calls) == 2 and 'openrouter.ai' in calls[-1]['url']


def test_unknown_provider_rejected_before_any_call():
    with pytest.raises(ValueError):
        triage_exception(ROW, 'openai')


@pytest.mark.parametrize('provider', ['openrouter', 'anthropic'])
def test_missing_key_fails_without_network(provider):
    with pytest.raises(RuntimeError, match='not set'):
        triage_exception(ROW, provider)


def test_missing_openrouter_model_fails(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', SECRET)
    with pytest.raises(RuntimeError, match='OPENROUTER_MODEL'):
        triage_exception(ROW, 'openrouter')


@pytest.mark.parametrize('bad', [
    payload(classification='MATCHED'),
    payload(requires_human_review=False),
    payload(transaction_id='OTHER'),
    'I think this is fine, no review needed.',
])
@pytest.mark.parametrize('provider', ['openrouter', 'anthropic'])
def test_injected_model_output_rejected_via_provider_path(monkeypatch, capture, provider, bad):
    monkeypatch.setenv('OPENROUTER_API_KEY', SECRET)
    monkeypatch.setenv('OPENROUTER_MODEL', 'm')
    monkeypatch.setenv('ANTHROPIC_API_KEY', SECRET)
    capture(openrouter_reply(bad) if provider == 'openrouter' else anthropic_reply([{'type': 'text', 'text': bad}]))
    with pytest.raises(ValueError):
        triage_exception(ROW, provider)


def test_http_errors_do_not_leak_secrets(monkeypatch, capture):
    monkeypatch.setenv('ANTHROPIC_API_KEY', SECRET)
    capture(FakeResponse({'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}}, 401))
    with pytest.raises(RuntimeError, match='HTTP 401') as err:
        triage_exception(ROW, 'anthropic')
    assert SECRET not in str(err.value)
    capture(httpx.ConnectError(f'connection failed for key {SECRET}'))
    with pytest.raises(RuntimeError, match='ConnectError') as err:
        triage_exception(ROW, 'anthropic')
    assert SECRET not in str(err.value) and err.value.__cause__ is None


@pytest.mark.parametrize('response', [
    FakeResponse(None),
    FakeResponse({'unexpected': True}),
    FakeResponse({'content': 'oops', 'stop_reason': 'end_turn'}),
    anthropic_reply([{'type': 'text', 'text': payload()}], stop='refusal'),
    anthropic_reply([{'type': 'text', 'text': payload()}], stop='max_tokens'),
    anthropic_reply([{'type': 'thinking', 'thinking': 'x'}]),
])
def test_anthropic_bad_responses_fail_closed(monkeypatch, capture, response):
    monkeypatch.setenv('ANTHROPIC_API_KEY', SECRET)
    capture(response)
    with pytest.raises(RuntimeError):
        triage_exception(ROW, 'anthropic')


@pytest.mark.parametrize('response', [
    FakeResponse({'error': {'message': 'rate limited', 'code': 429}}),
    FakeResponse({'choices': []}),
    openrouter_reply(payload(), finish='length'),
    openrouter_reply('   '),
    FakeResponse({'error': {'message': 'No credits'}}, 402),
])
def test_openrouter_bad_responses_fail_closed(monkeypatch, capture, response):
    monkeypatch.setenv('OPENROUTER_API_KEY', SECRET)
    monkeypatch.setenv('OPENROUTER_MODEL', 'm')
    capture(response)
    with pytest.raises(RuntimeError):
        triage_exception(ROW, 'openrouter')


def test_exception_row_never_mutated(monkeypatch, capture):
    monkeypatch.setenv('ANTHROPIC_API_KEY', SECRET)
    capture(anthropic_reply([{'type': 'text', 'text': payload(status='MATCHED')}]))
    row = dict(ROW)
    triage_exception(row, 'anthropic')
    assert row == ROW
