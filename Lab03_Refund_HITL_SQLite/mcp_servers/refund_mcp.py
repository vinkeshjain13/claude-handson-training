from mcp.server.fastmcp import FastMCP
from src.core import tx_lookup, policy, propose, get_request, history, list_pending
mcp=FastMCP('refund-investigator')

@mcp.tool()
def lookup_transaction(transaction_id: str) -> dict:
    """Read one synthetic payment transaction by ID (example TX1001)."""
    return tx_lookup(transaction_id) or {'error':'Not found'}

@mcp.tool()
def check_refund_policy(transaction_id: str) -> dict:
    """Fetch evidence and maximum permitted refund for a transaction."""
    return policy(transaction_id)

@mcp.tool()
def submit_refund_proposal(transaction_id: str, proposed_paise: int, justification: str) -> dict:
    """Propose only. NEVER authorizes or executes refund. Amount uses integer paise (1250000 = INR 12500)."""
    try: return propose(transaction_id,proposed_paise,justification)
    except (ValueError,TypeError) as e: return {'error':str(e)}

@mcp.tool()
def get_refund_request(request_id: int) -> dict:
    """Read status and amounts of one refund request."""
    return get_request(request_id) or {'error':'Not found'}

@mcp.tool()
def get_refund_audit(request_id: int) -> list[dict]:
    """Read immutable-by-tool history of proposal and reviewer decisions."""
    return history(request_id)

@mcp.tool()
def get_pending_approvals() -> list[dict]:
    """Read all pending requests. Read-only."""
    return list_pending()

if __name__=='__main__': mcp.run(transport='stdio')
