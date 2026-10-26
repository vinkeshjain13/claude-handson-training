from mcp.server.fastmcp import FastMCP
from src.reader_core import schema,ticket,tickets,history
mcp=FastMCP('service-desk-reader')
@mcp.tool()
def get_database_schema()->dict:
    """Discover allowed SQLite tables, columns and types. Read-only."""
    return schema()
@mcp.tool()
def get_ticket_details(ticket_id:str)->dict:
    """Read a service ticket and its related asset."""
    return ticket(ticket_id)
@mcp.tool()
def list_tickets(status:str='ALL')->list[dict] | dict:
    """List service tickets; optional status ALL/OPEN/IN_REVIEW/RESOLVED."""
    return tickets(status)
@mcp.tool()
def get_change_history(ticket_id:str)->list[dict]:
    """Read immutable audit event entries for a ticket."""
    return history(ticket_id)
if __name__=='__main__':mcp.run(transport='stdio')
