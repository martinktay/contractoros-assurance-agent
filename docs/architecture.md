# Architectural Design — ContractorOS Assurance Agent

This document explains the architecture, event design, and security boundaries implemented in the ContractorOS Assurance Agent repository.

## Component Overview

```
                 +--------------------------------------------+
                 |                  DEMO UI                   |
                 |       Vite + React (Tabs: Tower, Profile,   |
                 |       Decisions, System Timeline)          |
                 +----------------------+---------------------+
                                        | HTTP Requests (Port 3000 -> 8000)
                                        v
                 +--------------------------------------------+
                 |                 API Layer                  |
                 |            FastAPI / Backend (main.py)     |
                 +-------------+------------------+-----------+
                               |                  |
                               | Trigger Event    | Read/Write State
                               v                  v
                 +-------------+------+    +------+-----------+
                 |     Event Service  |    |    Data Store    |
                 |      (event_bus)   |    |    (JSON File)   |
                 +-------------+------+    +------------------+
                               |
                               | Dispatches Async Background Task
                               v
                 +-------------+------------------------------+
                 |           Strands Agent Runtime            |
                 |      Executes custom system prompts        |
                 |      using model provider (Bedrock/Mock)   |
                 +---------------------+----------------------+
                                       |
                     Invokes Tools     | Evaluates Autonomy
                     in sequence       v
                 +---------------------+----------------------+
                 |               Policy Gate                  |
                 |          Defines AUTO vs HUMAN             |
                 |          autonomy boundaries               |
                 +---------------------+----------------------+
                                       |
                       Permitted       | Blocked (High Risk)
                       Action          v
                                 +-----+----------------------+
                                 |         Escalation         |
                                 | Creates Human Review Case  |
                                 +----------------------------+
```

---

## The Strands Agent reasoning Loop

When a document is uploaded, the Strands agent is activated and executes the following sequence:

1.  **Acquire Context:** Calls `get_contractor`, `get_evidence`, and `get_applicable_requirements` to pull current status, requirement checklist, and raw file references.
2.  **Semantic Fact Extraction:** If a document is newly uploaded and unclassified, the agent calls `classify_and_extract_evidence`. This uses the underlying Bedrock model (or Mock model) to parse dates, issuer details, and confidence scores.
3.  **Deterministic Gap Analysis:** Calls `map_evidence_to_requirements` which automatically matches documents against target requirements. It identifies missing files, calculates expirations, and evaluates extraction confidence.
4.  **Autonomy Governance (Policy Gate):** Calls `evaluate_policy_and_determine_action` before executing any status changes.
    *   **Low Risk Actions** (e.g. dispatching reminders, asking for missing uploads) are executed automatically (`AUTO`).
    *   **High Risk Actions** (e.g. approving a contractor to `READY` status) are checked against the contractor's risk level. If risk is LOW (Alpha), it permits auto-approval. If risk is MEDIUM/HIGH, the Policy Gate returns `BLOCKED`, and the agent escalates by calling `create_human_review`.
5.  **Audit Trace Logging:** Every step is logged in the `AuditEvent` history database to ensure full accountability and visibility into the agent's actions without exposing private chain-of-thought blocks.

---

## Security Model (Prompt-Injection Defense)

1.  **Input Isolation:** In `classify_and_extract_evidence`, the raw untrusted document content is wrapped inside explicit delimiters (`[UNTRUSTED DOCUMENT START]` and `[UNTRUSTED DOCUMENT END]`) separating it from the system instruction blocks.
2.  **Defense-in-depth Sanitization:** Before sending document text to the model, the backend scans the raw content for instruction-override patterns (e.g. `ignore previous instructions`).
3.  **Low Confidence Safeguards:** If an injection attempt is detected or the model returns a low confidence extraction score (< 0.70), the policy engine overrides the action risk level to `HIGH`, forces the document status to `AMBIGUOUS`, blocks any automatic state changes, and routes the contractor to manual Human Review immediately.
