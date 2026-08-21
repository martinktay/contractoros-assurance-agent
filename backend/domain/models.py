from datetime import datetime, date
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

class Contractor(BaseModel):
    id: str
    name: str
    service_category: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    assurance_status: Literal["READY", "PARTIALLY_READY", "NOT_READY", "REVIEW_REQUIRED"]
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    incorporation_date: Optional[str] = None
    assigned_officer: Optional[str] = None
    safety_score: Optional[int] = None
    address: Optional[str] = None

class Requirement(BaseModel):
    id: str
    name: str
    description: str
    jurisdiction: str
    mandatory: bool
    validity_rules: dict[str, Any] = Field(default_factory=dict) # e.g. {"valid_duration_days": 365}
    evidence_types: list[str] # Document types that satisfy this requirement, e.g. ["HSE_POLICY"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]

class Evidence(BaseModel):
    id: str
    contractor_id: str
    document_name: str
    document_type: str # Classified document type (e.g. INSURANCE_CERTIFICATE, HSE_POLICY)
    uploaded_at: str # ISO Datetime string
    valid_from: Optional[str] = None # ISO Date string or None
    valid_until: Optional[str] = None # ISO Date string or None
    issuer: Optional[str] = None
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    status: Literal["VALID", "EXPIRING", "MISSING", "INSUFFICIENT", "CONFLICTING", "AMBIGUOUS"]
    source_reference: str # Simulated OCR/parse contents of the text file

class HumanDecision(BaseModel):
    id: str
    review_case_id: str
    contractor_id: str
    agent_recommendation: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    decision: Literal["APPROVE_RECOMMENDATION", "OVERRIDE", "REQUEST_MORE_EVIDENCE", "REJECT_FINDING", "ESCALATE"]
    reviewer: str
    reason: str
    created_at: str # ISO Datetime string

class HumanReview(BaseModel):
    id: str
    contractor_id: str
    issue: str
    recommended_action: str
    status: Literal["PENDING", "RESOLVED"]
    created_at: str
    resolved_at: Optional[str] = None
    decision_id: Optional[str] = None

class AuditEvent(BaseModel):
    id: str
    timestamp: str # ISO Datetime string
    event_type: str # e.g., DOCUMENT_UPLOADED, ACTION_BLOCKED, etc.
    agent_run_id: str
    contractor_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    policy_decision: Optional[str] = None
    human_review_id: Optional[str] = None
