import uuid
from datetime import datetime
from typing import Any, Optional

from backend.database.store import db
from backend.domain.models import AuditEvent

def log_event(
    event_type: str,
    contractor_id: str,
    details: dict[str, Any],
    policy_decision: Optional[str] = None,
    human_review_id: Optional[str] = None
) -> AuditEvent:
    """Helper to construct, save, and return an AuditEvent."""
    event = AuditEvent(
        id=f"evt_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now().isoformat(),
        event_type=event_type,
        agent_run_id=getattr(db, "current_run_id", "system"),
        contractor_id=contractor_id,
        details=details,
        policy_decision=policy_decision,
        human_review_id=human_review_id
    )
    db.save_audit_event(event)
    return event
