from mcp.server.fastmcp import FastMCP
from src.writer_core import update
mcp=FastMCP('service-desk-writer')
@mcp.tool()
def update_ticket(ticket_id:str,new_status:str,investigation_note:str,change_reason:str,confirm:bool=False)->dict:
    """Update a synthetic ticket with explicit confirmation flag. Allowed transitions only; auditable. Request user confirmation before calling with confirm=True. This flag is not production authorization."""
    return update(ticket_id,new_status,investigation_note,change_reason,confirm)
if __name__=='__main__':mcp.run(transport='stdio')
