from backend.tools.contractor_tools import get_contractor
from backend.tools.requirement_tools import get_applicable_requirements
from backend.tools.evidence_tools import get_evidence, classify_and_extract_evidence, map_evidence_to_requirements
from backend.tools.action_tools import (
    change_assurance_status,
    send_expiry_reminder,
    request_missing_evidence,
    create_human_review
)
from backend.tools.policy_tools import evaluate_policy_and_determine_action

# Master list of tools for the Strands agent
ALL_TOOLS = [
    get_contractor,
    get_applicable_requirements,
    get_evidence,
    classify_and_extract_evidence,
    map_evidence_to_requirements,
    evaluate_policy_and_determine_action,
    change_assurance_status,
    send_expiry_reminder,
    request_missing_evidence,
    create_human_review,
]

__all__ = [
    "get_contractor",
    "get_applicable_requirements",
    "get_evidence",
    "classify_and_extract_evidence",
    "map_evidence_to_requirements",
    "evaluate_policy_and_determine_action",
    "change_assurance_status",
    "send_expiry_reminder",
    "request_missing_evidence",
    "create_human_review",
    "ALL_TOOLS",
]
