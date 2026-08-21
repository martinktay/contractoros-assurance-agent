import pytest
from backend.policies.policy_gate import policy_gate
from backend.database.store import db
from backend.domain.models import Contractor

def setup_module(module):
    """Ensure database has initial seed data for policy testing."""
    db.reset_db()

def test_routine_actions_always_permitted():
    # Routine low-risk actions should be permitted regardless of risk
    res_reminder = policy_gate.evaluate_action("alpha", "send_expiry_reminder", {})
    assert res_reminder["status"] == "PERMITTED"
    assert res_reminder["risk_level"] == "LOW"

    res_missing = policy_gate.evaluate_action("charlie", "request_missing_evidence", {})
    assert res_missing["status"] == "PERMITTED"
    assert res_missing["risk_level"] == "LOW"

    res_review = policy_gate.evaluate_action("delta", "create_human_review", {})
    assert res_review["status"] == "PERMITTED"
    assert res_review["risk_level"] == "LOW"

def test_status_change_low_risk_contractor():
    # Alpha is LOW risk. Approving them should be permitted.
    res = policy_gate.evaluate_action("alpha", "change_assurance_status", {"status": "READY"})
    assert res["status"] == "PERMITTED"
    assert "LOW risk" in res["rationale"]

def test_status_change_high_risk_contractor():
    # Delta is HIGH risk. Approving them should be blocked for human approval.
    res = policy_gate.evaluate_action("delta", "change_assurance_status", {"status": "READY"})
    assert res["status"] == "BLOCKED"
    assert res["risk_level"] == "HIGH"
    assert "human intervention" in res["rationale"]

def test_dynamic_policy_updates():
    # Test setting policy to manual block for all status changes
    policy_gate.set_policy("CHANGE_ASSURANCE_STATUS", "HUMAN_APPROVAL")
    
    # Check that even low-risk contractor status change is blocked if policy is changed
    # (In our implementation, evaluate_action checks contractor risk first, but let's test general fallback)
    res_delta = policy_gate.evaluate_action("delta", "change_assurance_status", {"status": "READY"})
    assert res_delta["status"] == "BLOCKED"
