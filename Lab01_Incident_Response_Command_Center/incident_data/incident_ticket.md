# INC-2026-104 | Payment Gateway Latency and Failed Checkouts

Environment: SYNTHETIC | Date: 2026-10-24 | Priority: P1

10:15 IST onward: checkout timeouts rose; some customers retried payment attempts. Operations reported intermittent 5xx on `/api/payments/charge` and `/api/payments/status`. Your task is to determine the most likely cause, separate evidence from hypotheses, and recommend a safe recovery plan. Do NOT change any infrastructure.

Known at intake: last deployment between 09:45 and 10:00; unusual authentication traffic also observed. Evidence is provided in the adjacent files. Timestamps are IST (+05:30).
