import os
import logging
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.database.store import db
from backend.domain.models import Evidence, HumanDecision, HumanReview, Contractor
from backend.domain.seed_data import SIMULATED_DOCUMENTS
from backend.events.event_bus import event_bus
from backend.agents.assurance_agent import run_assurance_flow
from backend.policies.policy_gate import policy_gate
from backend.audit.logger import log_event

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main")

app = FastAPI(title="ContractorOS Assurance Agent API")

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For hackathon simplicity, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register event handlers
event_bus.subscribe("DOCUMENT_UPLOADED", run_assurance_flow)

# Request schemas
class DocumentUploadRequest(BaseModel):
    document_name: str
    document_text: str

class DecisionRequest(BaseModel):
    decision: str # APPROVE_RECOMMENDATION, OVERRIDE, REQUEST_MORE_EVIDENCE, REJECT_FINDING, ESCALATE
    reviewer: str
    reason: str
    override_status: Optional[str] = None # For OVERRIDE

class PolicyUpdateRequest(BaseModel):
    capability: str
    policy: str # AUTO, HUMAN_APPROVAL

# --- API Routes ---

@app.get("/api/contractors")
def get_contractors():
    return db.get_contractors()

@app.get("/api/contractors/{contractor_id}")
def get_contractor(contractor_id: str):
    c = db.get_contractor(contractor_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contractor not found")
    return {
        "contractor": c,
        "evidence": db.get_evidence(contractor_id),
        "timeline": db.get_audit_events(contractor_id)
    }

@app.post("/api/contractors/{contractor_id}/upload")
def upload_document(contractor_id: str, payload: DocumentUploadRequest, background_tasks: BackgroundTasks):
    c = db.get_contractor(contractor_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contractor not found")
        
    evidence_id = f"ev_{payload.document_name.split('.')[0].lower()}"
    
    # Create the Evidence record
    evidence = Evidence(
        id=evidence_id,
        contractor_id=contractor_id,
        document_name=payload.document_name,
        document_type="UNCLASSIFIED",
        uploaded_at=datetime.now().isoformat(),
        status="MISSING", # Default state before agent runs
        source_reference=payload.document_text
    )
    db.save_evidence(evidence)
    
    # Log event
    log_event(
        event_type="DOCUMENT_UPLOADED",
        contractor_id=contractor_id,
        details={"document_name": payload.document_name, "evidence_id": evidence_id}
    )
    
    # Emit event to trigger Strands Agent loop in background
    event_bus.emit("DOCUMENT_UPLOADED", background_tasks, contractor_id=contractor_id)
    
    return {"message": "Document uploaded successfully. Agent flow triggered.", "evidence_id": evidence_id}

@app.get("/api/reviews")
def get_reviews():
    return db.get_human_reviews()

@app.post("/api/reviews/{review_id}/decide")
def submit_decision(review_id: str, payload: DecisionRequest):
    review = db.get_human_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review case not found")
        
    if review.status == "RESOLVED":
        raise HTTPException(status_code=400, detail="Review case is already resolved")
        
    decision_id = f"dec_{review_id.split('_')[1]}"
    decision = HumanDecision(
        id=decision_id,
        review_case_id=review_id,
        contractor_id=review.contractor_id,
        agent_recommendation=review.recommended_action,
        risk_level="HIGH", # Review escalations are high risk
        decision=payload.decision,
        reviewer=payload.reviewer,
        reason=payload.reason,
        created_at=datetime.now().isoformat()
    )
    db.save_human_decision(decision)
    
    # Update review status
    review.status = "RESOLVED"
    review.resolved_at = datetime.now().isoformat()
    review.decision_id = decision_id
    db.save_human_review(review)
    
    # Log decision event
    log_event(
        event_type="HUMAN_DECISION_RECORDED",
        contractor_id=review.contractor_id,
        details={
            "review_id": review_id,
            "decision": payload.decision,
            "reviewer": payload.reviewer,
            "reason": payload.reason
        },
        human_review_id=review_id
    )
    
    # --- RESUME WORKFLOW ---
    contractor = db.get_contractor(review.contractor_id)
    if contractor:
        old_status = contractor.assurance_status
        new_status = old_status
        
        if payload.decision == "APPROVE_RECOMMENDATION":
            # Apply recommendation: Approve/READY
            new_status = "READY"
        elif payload.decision == "OVERRIDE" and payload.override_status:
            new_status = payload.override_status
        elif payload.decision == "REQUEST_MORE_EVIDENCE":
            # Dispatch evidence request and set NOT_READY
            new_status = "NOT_READY"
            # Log simulated request
            log_event(
                event_type="ACTION_EXECUTED",
                contractor_id=review.contractor_id,
                details={
                    "action": "request_more_evidence",
                    "reason": payload.reason,
                    "recipient": f"compliance@{contractor.name.lower().replace(' ', '')}.com"
                }
            )
        elif payload.decision == "REJECT_FINDING":
            new_status = "NOT_READY"
        elif payload.decision == "ESCALATE":
            new_status = "REVIEW_REQUIRED"
            
        contractor.assurance_status = new_status
        db.save_contractor(contractor)
        
        # Log workflow resumption event
        log_event(
            event_type="WORKFLOW_RESUMED",
            contractor_id=review.contractor_id,
            details={
                "review_id": review_id,
                "old_status": old_status,
                "new_status": new_status,
                "decision": payload.decision,
                "reason": payload.reason
            }
        )
        
    return {"message": "Decision recorded and workflow resumed successfully.", "decision_id": decision_id}

@app.get("/api/policies")
def get_policies():
    return policy_gate.get_policies()

@app.post("/api/policies")
def update_policy(payload: PolicyUpdateRequest):
    policy_gate.set_policy(payload.capability, payload.policy)
    return {"message": "Policy updated successfully."}

@app.post("/api/reset")
def reset_database():
    db.reset_db()
    # Log reset
    log_event(
        event_type="READINESS_UPDATED",
        contractor_id="system",
        details={"message": "System database reset to seed data."}
    )
    return {"message": "Database successfully reset to seed data."}

@app.post("/api/contractors/{contractor_id}/trigger")
def trigger_agent_manually(contractor_id: str, background_tasks: BackgroundTasks):
    """Optional manual trigger endpoint for convenience."""
    event_bus.emit("DOCUMENT_UPLOADED", background_tasks, contractor_id=contractor_id)
    return {"message": f"Agent flow triggered for {contractor_id}"}
