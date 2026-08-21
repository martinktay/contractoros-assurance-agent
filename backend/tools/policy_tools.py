from strands import tool
from backend.policies.policy_gate import policy_gate

@tool
def evaluate_policy_and_determine_action(contractor_id: str, proposed_action: str, status_details: str = "") -> dict:
    """Evaluates the risk level and safety policies for a proposed action on a contractor.
    
    Checks if the action is permitted to execute automatically or if it must be blocked for human review.
    
    Args:
        contractor_id: The unique identifier for the contractor.
        proposed_action: The action the agent intends to take (e.g. 'send_expiry_reminder', 'change_assurance_status').
        status_details: Optional details (e.g. target status like 'READY' or 'REVIEW_REQUIRED').
        
    Returns:
        A dictionary containing:
        - status: 'PERMITTED' or 'BLOCKED'
        - risk_level: 'LOW' or 'HIGH'
        - rationale: Text description of the policy decision.
    """
    details = {}
    if status_details:
        details["status"] = status_details
        
    # Standardize action name mappings if LLM uses slightly different names
    action = proposed_action.lower()
    if "approve" in action or "status" in action:
        action_name = "change_assurance_status"
        details["status"] = "READY"
    elif "remind" in action:
        action_name = "send_expiry_reminder"
    elif "missing" in action or "request" in action:
        action_name = "request_missing_evidence"
    elif "review" in action or "escalate" in action:
        action_name = "create_human_review"
    else:
        action_name = proposed_action

    return policy_gate.evaluate_action(contractor_id, action_name, details)
