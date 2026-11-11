"""RV-040: optional Responses API adapter sharing the existing BudgetedClient.

All stages are strict JSON, with no internal tool calls and no retries.
"""
import json

from app.orchestration.evidence_planner import SCOPE_SCHEMA, SCOPE_INSTRUCTIONS
from app.orchestration.v3_planning_contract import PLAN_V3_SCHEMA, PLAN_V3_INSTRUCTIONS
from app.orchestration.v3_replanning_contract import REPLAN_SCHEMA, REPLAN_INSTRUCTIONS
from app.orchestration.v3_semantic_contracts import (
    INVENTORY_SCHEMA, ASSURANCE_SCHEMA, INVENTORY_INSTRUCTIONS, ASSURANCE_INSTRUCTIONS,
)
from app.generation.v3_answer_contract import (
    ANSWER_SCHEMA, VERIFICATION_SCHEMA, ANSWER_INSTRUCTIONS, VERIFY_INSTRUCTIONS,
)
from app.orchestration.live_provider import BudgetedClient

ASSURANCE_V3_ALIGN_INSTRUCTIONS = ASSURANCE_INSTRUCTIONS + "\n" + (
    "Assess exactly one row for each item in payload.requirements, and NO "
    "rows for payload.excluded_requirements. Excluded rows only delimit "
    "the question scope; do not cite them as answer support. Never invent "
    "requirement IDs or candidate unit IDs. If independent inventory "
    "reveals a material unresolved dependency, RETRIEVE_MORE may target an "
    "in-scope requirement even if its stated rule is already supported."
)

STAGES = {
    "scope_v3": (SCOPE_SCHEMA, SCOPE_INSTRUCTIONS),
    "plan_v3": (PLAN_V3_SCHEMA, PLAN_V3_INSTRUCTIONS),
    "replan_v3": (REPLAN_SCHEMA, REPLAN_INSTRUCTIONS),
    "inventory_v3": (INVENTORY_SCHEMA, INVENTORY_INSTRUCTIONS),
    "assurance_v3": (ASSURANCE_SCHEMA, ASSURANCE_V3_ALIGN_INSTRUCTIONS),
    "generate_v3": (ANSWER_SCHEMA, ANSWER_INSTRUCTIONS),
    "verify_v3": (VERIFICATION_SCHEMA, VERIFY_INSTRUCTIONS),
}


class LiveV3Provider:
    def __init__(self, client: BudgetedClient, model: str, max_output_tokens=4000):
        if not isinstance(client, BudgetedClient):
            raise TypeError("Shared BudgetedClient required")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Explicit model required")
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 8192:
            raise ValueError("Invalid per-call cap")
        self.client, self.model, self.max_output_tokens = client, model, max_output_tokens

    def invoke(self, stage, payload):
        if stage not in STAGES or not isinstance(payload, dict):
            raise ValueError("Unrecognized v3 stage or payload")
        schema, instructions = STAGES[stage]
        response = self.client.responses.create(
            model=self.model, instructions=instructions,
            input=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False, allow_nan=False)}],
            text={"format": {"type": "json_schema", "name": stage, "strict": True, "schema": schema}},
            max_output_tokens=self.max_output_tokens, store=False,
        )
        if getattr(response, "status", None) != "completed" or not getattr(response, "output_text", None):
            raise RuntimeError("Incomplete v3 provider response")
        for item in getattr(response, "output", ()) or ():
            for part in getattr(item, "content", ()) or ():
                if getattr(part, "type", None) == "refusal":
                    raise RuntimeError("Provider refused v3 stage")
        return response.output_text
