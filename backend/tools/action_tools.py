import uuid
from datetime import datetime
from strands import tool
from backend.database.store import db
from backend.domain.models import HumanReview, AuditEvent

@tool
def change_assurance_status(contractor_id: str, status: str) -> dict:
    """Updates the contractor's assurance status in the database.
    
    Args:
        contractor_id: The unique identifier for the contractor.
        status: The target status, e.g. 'READY', 'PARTIALLY_READY', 'NOT_READY', 'REVIEW_REQUIRED'.
        
    Returns:
        A dictionary containing the update result.
    """
    contractor = db.get_contractor(contractor_id)
    if contractor:
        old_status = contractor.assurance_status
        contractor.assurance_status = status
        db.save_contractor(contractor)
        
        # Log action event
        event = AuditEvent(
            id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(),
            event_type="READINESS_UPDATED",
            agent_run_id=getattr(db, "current_run_id", "system"),
            contractor_id=contractor_id,
            details={
                "action": "change_assurance_status",
                "old_status": old_status,
                "new_status": status,
                "rationale": f"Readiness state updated to {status}."
            }
        )
        db.save_audit_event(event)
        return {"success": True, "contractor_id": contractor_id, "status": status}
    return {"error": f"Contractor '{contractor_id}' not found."}

@tool
def send_expiry_reminder(contractor_id: str, evidence_id: str) -> dict:
    """Sends an automated email notification reminder to the contractor about expiring evidence.
    
    Args:
        contractor_id: The unique identifier for the contractor.
        evidence_id: The ID of the evidence document that is expiring soon.
        
    Returns:
        A dictionary detailing the sent email reminder parameters.
    """
    contractor = db.get_contractor(contractor_id)
    evidence = db.get_evidence_item(evidence_id)
    
    if not contractor or not evidence:
        return {"error": "Contractor or Evidence not found."}
        
    # Simulate email dispatch
    reminder_details = {
        "to": f"compliance@{contractor.name.lower().replace(' ', '')}.com",
        "subject": f"ACTION REQUIRED: Your document '{evidence.document_name}' is expiring soon",
        "body": f"Hello team,\n\nOur system detected that your General Liability Insurance ({evidence.document_name}) expires on {evidence.valid_until}.\nPlease upload a renewed certificate to maintain active assurance status.\n\nBest regards,\nContractorOS Assurance Agent",
        "dispatched_at": datetime.now().isoformat()
    }
    
    # Log action event
    event = AuditEvent(
        id=f"evt_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now().isoformat(),
        event_type="ACTION_EXECUTED",
        agent_run_id=getattr(db, "current_run_id", "system"),
        contractor_id=contractor_id,
        details={
            "action": "send_expiry_reminder",
            "evidence_id": evidence_id,
            "evidence_name": evidence.document_name,
            "recipient": reminder_details["to"],
            "subject": reminder_details["subject"]
        }
    )
    db.save_audit_event(event)
    
    return {"success": True, "details": reminder_details}

@tool
def request_missing_evidence(contractor_id: str, requirement_id: str) -> dict:
    """Dispatches a request to the contractor to upload missing mandatory document.
    
    Args:
        contractor_id: The unique identifier for the contractor.
        requirement_id: The ID of the requirement that lacks evidence.
        
    Returns:
        A dictionary detailing the requested missing evidence.
    """
    contractor = db.get_contractor(contractor_id)
    requirement = db.get_requirement(requirement_id)
    
    if not contractor or not requirement:
        return {"error": "Contractor or Requirement not found."}
        
    request_details = {
        "to": f"compliance@{contractor.name.lower().replace(' ', '')}.com",
        "subject": f"ACTION REQUIRED: Missing mandatory requirement '{requirement.name}'",
        "body": f"Hello team,\n\nWe require evidence for the following mandatory requirement: '{requirement.name}' ({requirement.description}).\nPlease upload a valid document as soon as possible.\n\nBest regards,\nContractorOS Assurance Agent",
        "dispatched_at": datetime.now().isoformat()
    }
    
    # Log action event
    event = AuditEvent(
        id=f"evt_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now().isoformat(),
        event_type="ACTION_EXECUTED",
        agent_run_id=getattr(db, "current_run_id", "system"),
        contractor_id=contractor_id,
        details={
            "action": "request_missing_evidence",
            "requirement_id": requirement_id,
            "requirement_name": requirement.name,
            "recipient": request_details["to"],
            "subject": request_details["subject"]
        }
    )
    db.save_audit_event(event)
    
    return {"success": True, "details": request_details}

@tool
def create_human_review(contractor_id: str, issue: str, recommended_action: str) -> dict:
    """Escalates case to the Decisions Required queue for human intervention, blocking status changes.
    
    Args:
        contractor_id: The unique identifier for the contractor.
        issue: Brief explanation of the anomaly, low confidence extraction, or prompt injection.
        recommended_action: Recommended remediation step.
        
    Returns:
        A dictionary showing the generated HumanReview review record.
    """
    review_id = f"rev_{uuid.uuid4().hex[:8]}"
    review = HumanReview(
        id=review_id,
        contractor_id=contractor_id,
        issue=issue,
        recommended_action=recommended_action,
        status="PENDING",
        created_at=datetime.now().isoformat()
    )
    db.save_human_review(review)
    
    # Also set contractor status to REVIEW_REQUIRED
    contractor = db.get_contractor(contractor_id)
    if contractor:
        contractor.assurance_status = "REVIEW_REQUIRED"
        db.save_contractor(contractor)
        
    # Log review creation
    event = AuditEvent(
        id=f"evt_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now().isoformat(),
        event_type="HUMAN_REVIEW_CREATED",
        agent_run_id=getattr(db, "current_run_id", "system"),
        contractor_id=contractor_id,
        details={
            "action": "create_human_review",
            "review_id": review_id,
            "issue": issue,
            "recommended_action": recommended_action
        },
        human_review_id=review_id
    )
    db.save_audit_event(event)
    
    return {"success": True, "review_id": review_id, "review": review.model_dump()}
