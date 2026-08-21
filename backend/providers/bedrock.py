import os
import json
import logging
import uuid
from collections.abc import AsyncGenerator, AsyncIterable
from typing import Any, TypeVar, cast
from pydantic import BaseModel
from typing_extensions import override

# Try to import from strands
from strands.models.model import Model
from strands.models.bedrock import BedrockModel
from strands.types.content import Messages, SystemContentBlock
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolChoice, ToolSpec

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

class MockModel(Model):
    """Mock model provider for Strands to allow local/offline execution and verification.
    
    Simulates tool calling and final response text for the ContractorOS Assurance Agent scenarios
    without requiring active AWS Bedrock credentials.
    """

    def __init__(self, model_id: str = "mock-claude-3-5-sonnet", **kwargs: Any):
        self.model_id = model_id
        self.config = {"model_id": model_id}

    @override
    def update_config(self, **model_config: Any) -> None:
        self.config.update(model_config)

    @override
    def get_config(self) -> Any:
        return self.config

    @override
    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        """Simulates structured output extraction."""
        # Check prompt to see what type of structured output is being requested
        prompt_text = str(prompt).lower()
        
        # Default mock extraction return
        extracted_data = {}
        
        if "classify" in prompt_text or "extract" in prompt_text:
            # Fact extraction schema
            if "bravo" in prompt_text:
                extracted_data = {
                    "document_type": "INSURANCE_CERTIFICATE",
                    "issuer": "Bravo Mutual Insurance",
                    "valid_from": "2025-01-01",
                    "valid_until": "2026-08-30", # Expiring soon relative to Aug 2026
                    "extracted_fields": {"policy_number": "POL-BRAVO-789"},
                    "confidence": 0.95
                }
            elif "charlie" in prompt_text:
                extracted_data = {
                    "document_type": "HSE_POLICY",
                    "issuer": "Charlie Corp HSE Board",
                    "valid_from": "2025-06-01",
                    "valid_until": "2027-06-01",
                    "extracted_fields": {"policy_statement": "Incomplete policy content"},
                    "confidence": 0.80
                }
            elif "delta" in prompt_text:
                extracted_data = {
                    "document_type": "REGULATORY_PERMIT",
                    "issuer": "Unknown Authority",
                    "valid_from": "2025-01-01",
                    "valid_until": "2026-12-31",
                    "extracted_fields": {"category": "Ambiguous/Unrecognized Category"},
                    "confidence": 0.60 # Low confidence trigger
                }
            elif "echo" in prompt_text:
                # Injection attempt
                extracted_data = {
                    "document_type": "INJECTION_ATTEMPT",
                    "issuer": "Malicious Entity",
                    "valid_from": "2026-01-01",
                    "valid_until": "2026-12-31",
                    "extracted_fields": {"prompt_injection_detected": True},
                    "confidence": 0.99
                }
            else: # Alpha
                extracted_data = {
                    "document_type": "INSURANCE_CERTIFICATE",
                    "issuer": "Alpha Shield Insurance",
                    "valid_from": "2026-01-01",
                    "valid_until": "2027-12-31", # Valid
                    "extracted_fields": {"policy_number": "POL-ALPHA-123"},
                    "confidence": 0.98
                }
        
        # Instantiate output model
        obj = output_model(**extracted_data)
        yield {"output": obj}

    @override
    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        invocation_state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[StreamEvent]:
        """Streams mock events simulating model thought, tool calls, and text output."""
        
        # Find the last message
        last_message = messages[-1]
        last_content = last_message.get("content", [])
        
        prompt_text = ""
        for block in last_content:
            if "text" in block:
                prompt_text += block["text"]
        
        prompt_text = prompt_text.lower()
        
        # Determine contractor context from history
        contractor_id = None
        for name in ["alpha", "bravo", "charlie", "delta", "echo"]:
            if name in prompt_text or any(name in str(msg).lower() for msg in messages):
                contractor_id = name
                break

        if contractor_id is None:
            # If no contractor context is found, return a generic greeting/help text
            greeting = "Hello! ContractorOS Assurance Agent is online. Specify a contractor (Alpha, Bravo, Charlie, Delta, Echo) to trigger the compliance assessment workflow."
            async for event in self._generate_text_response(greeting):
                yield event
            return

        # Check if final action has already been executed to prevent infinite loops
        has_final_action_run = (
            any(
                block.get("toolUse", {}).get("name") in [
                    "change_assurance_status",
                    "send_expiry_reminder",
                    "request_missing_evidence",
                    "create_human_review"
                ]
                for msg in messages
                for block in msg.get("content", [])
                if isinstance(block, dict)
            )
        )
        
        # Check if we have tool results in the history
        has_contractor_result = any("get_contractor" in str(msg) for msg in messages)
        has_evidence_result = any("get_evidence" in str(msg) for msg in messages)
        has_requirements_result = any("get_applicable_requirements" in str(msg) for msg in messages)
        
        # Determine current state of the agent loop based on conversation history
        if not (has_contractor_result and has_evidence_result and has_requirements_result):
            # Phase 1: Retrieve context
            tool_calls = [
                ("get_contractor", {"contractor_id": contractor_id}),
                ("get_evidence", {"contractor_id": contractor_id}),
                ("get_applicable_requirements", {"contractor_id": contractor_id})
            ]
            async for event in self._generate_tool_calls(tool_calls):
                yield event
        elif not any("map_evidence_to_requirements" in str(msg) for msg in messages):
            # Phase 2: Perform mapping tool call
            async for event in self._generate_tool_calls([
                ("map_evidence_to_requirements", {"contractor_id": contractor_id})
            ]):
                yield event
        elif not any("evaluate_policy_and_determine_action" in str(msg) for msg in messages):
            # Phase 3: Perform policy gate tool call
            # We determine the action based on the contractor
            action = "APPROVE"
            if contractor_id == "bravo":
                action = "SEND_EXPIRY_REMINDER"
            elif contractor_id == "charlie":
                action = "REQUEST_MISSING_EVIDENCE"
            elif contractor_id == "delta":
                action = "BLOCK_FOR_REVIEW"
            elif contractor_id == "echo":
                action = "BLOCK_FOR_REVIEW"
                
            async for event in self._generate_tool_calls([
                ("evaluate_policy_and_determine_action", {
                    "contractor_id": contractor_id, 
                    "proposed_action": action
                })
            ]):
                yield event
        elif not has_final_action_run:
            # Phase 4: Execute final action tool call
            final_tools = []
            if contractor_id == "alpha":
                final_tools.append(("change_assurance_status", {"contractor_id": "alpha", "status": "READY"}))
            elif contractor_id == "bravo":
                final_tools.append(("send_expiry_reminder", {"contractor_id": "bravo", "evidence_id": "ev_bravo_insurance"}))
                final_tools.append(("change_assurance_status", {"contractor_id": "bravo", "status": "PARTIALLY_READY"}))
            elif contractor_id == "charlie":
                final_tools.append(("request_missing_evidence", {"contractor_id": "charlie", "requirement_id": "HSE-01"}))
                final_tools.append(("change_assurance_status", {"contractor_id": "charlie", "status": "NOT_READY"}))
            elif contractor_id == "delta":
                final_tools.append(("create_human_review", {
                    "contractor_id": "delta", 
                    "issue": "Regulatory permit service-category is unrecognized/ambiguous.",
                    "recommended_action": "Verify service category matches authorized scopes"
                }))
            elif contractor_id == "echo":
                final_tools.append(("create_human_review", {
                    "contractor_id": "echo", 
                    "issue": "Prompt injection attempt detected within evidence document.",
                    "recommended_action": "Inspect document and verify contractor credentials manually"
                }))
            
            async for event in self._generate_tool_calls(final_tools):
                yield event
        else:
            # Phase 5: Return final text response summarizing findings
            final_text = ""
            if contractor_id == "alpha":
                final_text = "Contractor Alpha has valid and complete evidence. The contractor is fully compliant and has been set to READY status."
            elif contractor_id == "bravo":
                final_text = "Contractor Bravo has insurance expiring soon (within 30 days). A simulated renewal reminder has been sent automatically."
            elif contractor_id == "charlie":
                final_text = "Contractor Charlie is missing the mandatory HSE Policy document. An automated request for the missing evidence has been triggered."
            elif contractor_id == "delta":
                final_text = "Contractor Delta has ambiguous evidence with low confidence. Status change blocked; created human review case."
            elif contractor_id == "echo":
                final_text = "WARNING: Contractor Echo document contains a prompt-injection attempt! System instructions preserved. The document has been flagged and blocked for manual human review."
                
            async for event in self._generate_text_response(final_text):
                yield event

    async def _generate_tool_calls(self, tool_calls: list[tuple[str, dict]]) -> AsyncGenerator[StreamEvent, None]:
        """Helper to yield a set of tool call events."""
        yield {"messageStart": {"role": "assistant"}}
        
        for idx, (name, args) in enumerate(tool_calls):
            call_id = f"call_{uuid.uuid4().hex[:8]}"
            yield {
                "contentBlockStart": {
                    "index": idx,
                    "start": {
                        "toolUse": {
                            "toolUseId": call_id,
                            "name": name
                        }
                    }
                }
            }
            yield {
                "contentBlockDelta": {
                    "index": idx,
                    "delta": {
                        "toolUse": {
                            "input": json.dumps(args)
                        }
                    }
                }
            }
            yield {
                "contentBlockStop": {
                    "index": idx
                }
            }
            
        yield {"messageStop": {"stopReason": "tool_use"}}

    async def _generate_text_response(self, text: str) -> AsyncGenerator[StreamEvent, None]:
        """Helper to yield a plain text response."""
        yield {"messageStart": {"role": "assistant"}}
        yield {
            "contentBlockStart": {
                "index": 0,
                "start": {
                    "text": ""
                }
            }
        }
        
        # Stream text in small chunks to simulate streaming
        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            yield {
                "contentBlockDelta": {
                    "index": 0,
                    "delta": {
                        "text": chunk
                    }
                }
            }
            
        yield {
            "contentBlockStop": {
                "index": 0
            }
        }
        yield {"messageStop": {"stopReason": "end_turn"}}


def get_model() -> Model:
    """Factory to retrieve either the BedrockModel or the MockModel fallback based on config."""
    use_mock = os.getenv("USE_MOCK_MODEL", "true").lower() == "true"
    
    # Also verify if AWS credentials are set; if not, force mock mode to prevent crash
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not use_mock and aws_key and aws_secret:
        try:
            model_id = os.getenv("AWS_BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
            region = os.getenv("AWS_REGION", "us-west-2")
            logger.info(f"Initializing AWS Bedrock Model: {model_id} in {region}")
            return BedrockModel(model_id=model_id, region_name=region)
        except Exception as e:
            logger.warning(f"Failed to initialize Bedrock model: {e}. Falling back to MockModel.")
            return MockModel()
    else:
        logger.info("Using MockModel (Offline simulation mode)")
        return MockModel()
