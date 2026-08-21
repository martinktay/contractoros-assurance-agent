# ContractorOS Assurance Agent

**An autonomous contractor-assurance agent for high-risk industries, demonstrated through oil & gas contractor compliance workflows.**

Built for the **AWS Agents for Humans Hackathon** under the **Professional Agents** track.

---

## 1. The Problem
Contractor compliance in high-risk industries (such as Oil & Gas) is extremely document-heavy, repetitive, and vulnerable to oversights. Compliance managers spend hours manually reviewing insurance certificates, safety policies, and government permits to verify validity, categories, and issuers. 

## 2. The Solution
ContractorOS Assurance Agent automates the repetitive gathering and factual analysis of evidence while keeping critical, high-impact decisions strictly under human control. 

This is **not a generic chatbot**. It is an event-driven agent that activates automatically in the background on document upload, uses structured tools, checks a deterministic policy engine (risk gate), takes permitted routine actions, and escalates ambiguous or high-risk cases to compliance managers with full auditability.

---

## 3. Core Architecture & Strands Integration

```
                 +--------------------------------------------+
                 |                  DEMO UI                   |
                 |       Vite + React (Tabs: Tower, Profile,   |
                 |       Decisions, System Timeline)          |
                 +----------------------+---------------------+
                                        | HTTP Requests
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
                 +--------------------------------------------+
```

### Strands Agents SDK Role
The agent is powered by the **Strands Agents SDK** and is responsible for:
*   **Orchestration:** Managing the multi-step reasoning flow upon document upload.
*   **Tool Usage:** Choosing when to pull contractor details, map files, run risk gates, dispatch reminders, or create human reviews.
*   **Fact Extraction:** Using Claude 3.5 Sonnet on **Amazon Bedrock** to extract structured facts (dates, issuers, category parameters) from untrusted uploaded text files.

### Bounded Autonomy & Policy Gate
An explicit python policy gate governs the agent. The agent recommends an action, but a deterministic engine determines if it can run:
*   **Routine Low-Risk Actions** (e.g. sending expiring insurance reminders, requesting missing files) run automatically.
*   **High-Risk Status-Changing Actions** (e.g. changing status to `READY`) are blocked for human review if the contractor's profile is Medium/High risk.
*   **The agent cannot override this gate.** Uploaded content or prompt injection attempts cannot bypass these boundaries.

---

## 4. Human-in-the-Loop Model
The system exposes three distinct human involvement interfaces:
1.  **Policy-Setting Human:** Allows administrators to configure which capabilities (e.g. updating assurance status) execute automatically or require manual review.
2.  **Decision-Review Human:** A dedicated review queue highlighting the contractor, issue, extraction confidence, and options (Approve, Override, Request More Evidence, Reject, Escalate).
3.  **Accountability Human:** A verifiable system trace and audit timeline showing exactly what the agent did, what tools it called, and who approved each status update.

---

## 5. Security & Prompt-Injection Defense
*   **Context Isolation:** Raw document text is strictly wrapped in `[UNTRUSTED DOCUMENT]` delimiters in system instructions.
*   **Sanitization Filters:** Documents containing instructions like *"ignore previous instructions"* are automatically flagged by pre-parsing regex filters.
*   **Automated Escalation:** Any flagged documents have their extraction confidence minimized, status set to `AMBIGUOUS`, and are routed directly to manual review, preventing status changes.

---

## 6. Local Setup & Running

### Prerequisites
*   **Python 3.12+**
*   **Node.js 18+** & **npm**
*   **uv** (Python Package Manager, installed automatically via uv commands)

### 1. Configuration
Copy the environment template and configure settings:
```bash
cp .env.example .env
```
*By default, `USE_MOCK_MODEL=true` is enabled in `.env` so the repository runs instantly out-of-the-box without requiring AWS credentials.*

### 2. Install & Launch (Single Command)
Run the launcher script to install all dependencies and start both the backend API and frontend UI concurrently:
```bash
python start.py
```
*   **Frontend UI:** [http://localhost:3000](http://localhost:3000)
*   **Backend API:** [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 7. Testing & Scenarios Evaluation

The test suite validates the system's deterministic logic, policy gate enforcement, and prompt injection mitigation.

Run all tests:
```bash
uv run pytest
```

### Supported Test Scenarios
1.  **Contractor Alpha:** Fully compliant low-risk profile -> Evaluates autonomously to `READY` status.
2.  **Contractor Bravo:** Insurance expiring -> Identifies expiry, triggers reminder, downgrades status to `PARTIALLY_READY`.
3.  **Contractor Charlie:** Mandatory HSE file missing -> Logs gaps, triggers automated request for files, status set to `NOT_READY`.
4.  **Contractor Delta:** Ambiguous permit -> Low confidence category triggers safety policy block, status set to `REVIEW_REQUIRED`.
5.  **Contractor Echo:** Prompt injection payload -> Injection detected, auto status changes blocked, escalated to review.

---

## 8. AWS Model Access
To run the agent against actual foundation models, configure your AWS credentials in `.env` (`USE_MOCK_MODEL=false`) and ensure your IAM role has model invocation permissions in Amazon Bedrock for:
*   `us.anthropic.claude-3-5-sonnet-20241022-v2:0` (or similar Claude model ID configured in `AWS_BEDROCK_MODEL_ID`).
