import os
import json
import logging
from typing import Any, Optional
from datetime import datetime

from backend.domain.models import Contractor, Requirement, Evidence, HumanDecision, HumanReview, AuditEvent
from backend.domain.seed_data import SEED_REQUIREMENTS, SEED_CONTRACTORS

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "data.json")

class DataStore:
    """Local JSON-file based database controller for the hackathon."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._data = {"contractors": {}, "requirements": {}, "evidence": {}, "reviews": {}, "decisions": {}, "audit_events": []}
        self.load()

    def load(self) -> None:
        """Loads data from the JSON file. If it doesn't exist, seeds it."""
        if not os.path.exists(self.db_path):
            logger.info("Database file not found. Initializing with seed data...")
            self.seed()
            self.save()
            return

        try:
            with open(self.db_path, "r") as f:
                raw_data = json.load(f)
                # Safeguard against malformed JSON or missing keys
                self._data = {
                    "contractors": raw_data.get("contractors", {}),
                    "requirements": raw_data.get("requirements", {}),
                    "evidence": raw_data.get("evidence", {}),
                    "reviews": raw_data.get("reviews", {}),
                    "decisions": raw_data.get("decisions", {}),
                    "audit_events": raw_data.get("audit_events", [])
                }
        except Exception as e:
            logger.error(f"Error loading database: {e}. Re-seeding database.")
            self.seed()
            self.save()

    def save(self) -> None:
        """Saves current memory state to the JSON file."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save database to disk: {e}")

    def seed(self) -> None:
        """Seeds the database state with default contractors and requirements."""
        self._data = {
            "contractors": {c.id: c.model_dump() for c in SEED_CONTRACTORS},
            "requirements": {r.id: r.model_dump() for r in SEED_REQUIREMENTS},
            "evidence": {},
            "reviews": {},
            "decisions": {},
            "audit_events": []
        }

    def reset_db(self) -> None:
        """Resets database state completely back to initial seed data."""
        self.seed()
        self.save()

    # --- Contractors ---
    def get_contractor(self, contractor_id: str) -> Optional[Contractor]:
        c_dict = self._data["contractors"].get(contractor_id)
        if c_dict:
            return Contractor.model_validate(c_dict)
        return None

    def get_contractors(self) -> list[Contractor]:
        return [Contractor.model_validate(c) for c in self._data["contractors"].values()]

    def save_contractor(self, contractor: Contractor) -> None:
        self._data["contractors"][contractor.id] = contractor.model_dump()
        self.save()

    # --- Requirements ---
    def get_requirement(self, requirement_id: str) -> Optional[Requirement]:
        r_dict = self._data["requirements"].get(requirement_id)
        if r_dict:
            return Requirement.model_validate(r_dict)
        return None

    def get_requirements(self) -> list[Requirement]:
        return [Requirement.model_validate(r) for r in self._data["requirements"].values()]

    # --- Evidence ---
    def get_evidence(self, contractor_id: str) -> list[Evidence]:
        ev_list = []
        for ev in self._data["evidence"].values():
            if ev.get("contractor_id") == contractor_id:
                ev_list.append(Evidence.model_validate(ev))
        return ev_list

    def get_evidence_item(self, evidence_id: str) -> Optional[Evidence]:
        ev_dict = self._data["evidence"].get(evidence_id)
        if ev_dict:
            return Evidence.model_validate(ev_dict)
        return None

    def save_evidence(self, evidence: Evidence) -> None:
        self._data["evidence"][evidence.id] = evidence.model_dump()
        self.save()

    # --- Human Reviews ---
    def get_human_reviews(self) -> list[HumanReview]:
        return [HumanReview.model_validate(r) for r in self._data["reviews"].values()]

    def get_human_review(self, review_id: str) -> Optional[HumanReview]:
        r_dict = self._data["reviews"].get(review_id)
        if r_dict:
            return HumanReview.model_validate(r_dict)
        return None

    def save_human_review(self, review: HumanReview) -> None:
        self._data["reviews"][review.id] = review.model_dump()
        self.save()

    # --- Human Decisions ---
    def get_human_decisions(self) -> list[HumanDecision]:
        return [HumanDecision.model_validate(d) for d in self._data["decisions"].values()]

    def get_human_decision(self, decision_id: str) -> Optional[HumanDecision]:
        d_dict = self._data["decisions"].get(decision_id)
        if d_dict:
            return HumanDecision.model_validate(d_dict)
        return None

    def save_human_decision(self, decision: HumanDecision) -> None:
        self._data["decisions"][decision.id] = decision.model_dump()
        self.save()

    # --- Audit Events ---
    def get_audit_events(self, contractor_id: Optional[str] = None) -> list[AuditEvent]:
        events = [AuditEvent.model_validate(e) for e in self._data["audit_events"]]
        if contractor_id:
            events = [e for e in events if e.contractor_id == contractor_id]
        # Sort by timestamp (newest first for UI timeline)
        events.sort(key=lambda x: x.timestamp, reverse=True)
        return events

    def save_audit_event(self, event: AuditEvent) -> None:
        self._data["audit_events"].append(event.model_dump())
        self.save()

# Global database instance
db = DataStore()
