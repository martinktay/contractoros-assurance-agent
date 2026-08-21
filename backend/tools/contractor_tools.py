from strands import tool
from backend.database.store import db

@tool
def get_contractor(contractor_id: str) -> dict:
    """Fetches contractor information by contractor ID.
    
    Args:
        contractor_id: The unique identifier for the contractor (e.g. 'alpha', 'bravo').
        
    Returns:
        A dictionary containing contractor name, service category, risk level, and current assurance status.
    """
    contractor = db.get_contractor(contractor_id)
    if contractor:
        return contractor.model_dump()
    return {"error": f"Contractor with ID '{contractor_id}' not found."}
