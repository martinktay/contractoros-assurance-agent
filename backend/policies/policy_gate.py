import logging
from typing import Literal

from backend.database.store import db
from backend.domain.models import Contractor

logger = logging.getLogger(__name__)

# Capability settings stored in memory / default config
# Can be modified by the Policy-Setting Human in the UI
DEFAULT_CAPABILITY_POLICIES = {
    "READ_EVIDENCE": "AUTO",
    "CLASSIFY_EVIDENCE": "AUTO",
    "EXTRACT_EVIDENCE": "AUTO",
    "GET_REQUIREMENTS": "AUTO",
    "MAP_EVIDENCE_TO_REQUIREMENT": "AUTO",
    "REQUEST_MISSING_EVIDENCE": "AUTO",
    "SEND_EXPIRY_REMINDER": "AUTO",
    "CREATE_REVIEW": "AUTO",
    "CHANGE_ASSURANCE_STATUS": "HUMAN_APPROVAL", # Default for general status change
}

class PolicyGate:
    """Deterministic policy engine that governs agent autonomy and enforces boundaries."""
    
    def __init__(self):
        # We can store active policies in the store or memory
        self.policies = DEFAULT_CAPABILITY_POLICIES.copy()

    def set_policy(self, capability: str, policy: Literal["AUTO", "HUMAN_APPROVAL"]) -> None:
        """Allows a policy-setting human to dynamically adjust capability permissions."""
        if capability in self.policies:
            self.policies[capability] = policy
            logger.info(f"Policy updated: {capability} -> {policy}")

    def get_policies(self) -> dict[str, str]:
        return self.policies

    def evaluate_action(self, contractor_id: str, action_name: str, details: dict) -> dict:
        """Determines if the proposed action is permitted to execute automatically.
        
        Args:
            contractor_id: The ID of the contractor the action pertains to.
            action_name: The name of the proposed action (e.g. 'send_expiry_reminder', 'change_assurance_status').
            details: Extra parameters (like target status).
            
        Returns:
            A dictionary containing 'status' (PERMITTED | BLOCKED), 'risk_level' (LOW | HIGH), and 'rationale'.
        """
        contractor = db.get_contractor(contractor_id)
        if not contractor:
            return {"status": "BLOCKED", "risk_level": "HIGH", "rationale": "Contractor not found."}
            
        # 1. Low risk actions are always auto-permitted
        if action_name in ["send_expiry_reminder", "request_missing_evidence", "create_human_review"]:
            return {
                "status": "PERMITTED",
                "risk_level": "LOW",
                "rationale": f"Action '{action_name}' is classified as routine low-risk and is auto-permitted."
            }
            
        # 2. Status changes (approvals/suspensions) are high risk and subject to policy gate
        if action_name == "change_assurance_status":
            target_status = details.get("status")
            
            # Setting to REVIEW_REQUIRED is an escalation, always permitted
            if target_status == "REVIEW_REQUIRED":
                return {
                    "status": "PERMITTED",
                    "risk_level": "LOW",
                    "rationale": "Escalation to REVIEW_REQUIRED is always permitted."
                }
                
            # Approve Contractor (setting status to READY)
            if target_status == "READY":
                # Check current policy setting
                policy_setting = self.policies.get("CHANGE_ASSURANCE_STATUS", "HUMAN_APPROVAL")
                
                # Check contractor risk level
                # Alpha is LOW risk and fully compliant.
                # Policy: If contractor risk is LOW, we allow auto-approval.
                # If contractor risk is MEDIUM or HIGH, we block for human approval.
                if contractor.risk_level == "LOW":
                    return {
                        "status": "PERMITTED",
                        "risk_level": "LOW",
                        "rationale": f"Contractor '{contractor.name}' is LOW risk. Auto-approval is permitted."
                    }
                else:
                    return {
                        "status": "BLOCKED",
                        "risk_level": "HIGH",
                        "rationale": f"Contractor '{contractor.name}' is {contractor.risk_level} risk. Approvals require human intervention."
                    }
            
            # Suspend or fail Contractor (setting status to NOT_READY)
            if target_status == "NOT_READY":
                # By default, we let the agent auto-flag NOT_READY if documents are missing
                return {
                    "status": "PERMITTED",
                    "risk_level": "LOW",
                    "rationale": "Transitioning to NOT_READY is permitted to reflect missing requirements."
                }
                
        # Catch-all fallback: Block for human safety
        return {
            "status": "BLOCKED",
            "risk_level": "HIGH",
            "rationale": f"Action '{action_name}' is restricted by default safety policy."
        }

# Global Policy Gate instance
policy_gate = PolicyGate()
