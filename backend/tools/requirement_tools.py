from strands import tool
from backend.database.store import db

@tool
def get_applicable_requirements(contractor_id: str) -> list[dict]:
    """Retrieves all compliance requirements applicable to a contractor.
    
    Args:
        contractor_id: The unique identifier for the contractor.
        
    Returns:
        A list of dictionaries representing the applicable compliance requirements.
    """
    # For this demo pack, all requirements in the system apply to all contractors
    requirements = db.get_requirements()
    return [r.model_dump() for r in requirements]
