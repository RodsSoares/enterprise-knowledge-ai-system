"""Opt-in RV-042 Responses adapter; underlying v3 provider remains untouched.

The relevance stage uses the same shared BudgetedClient as all other calls.
"""
import json

from app.orchestration.v3_live_provider import LiveV3Provider, STAGES as V3_STAGES
from app.orchestration.v42_relevance_contract import RELEVANCE_SCHEMA, RELEVANCE_INSTRUCTIONS
from app.orchestration.v42_verification_contract import V42_VERIFICATION_SCHEMA, V42_VERIFY_INSTRUCTIONS

V42_STAGES = {**V3_STAGES, "relevance_v42": (RELEVANCE_SCHEMA, RELEVANCE_INSTRUCTIONS),
              "verify_v3": (V42_VERIFICATION_SCHEMA, V42_VERIFY_INSTRUCTIONS)}


class LiveV42Provider(LiveV3Provider):
    def invoke(self, stage, payload):
        if stage not in ("relevance_v42", "verify_v3"):
            return super().invoke(stage, payload)
        if not isinstance(payload, dict):
            raise ValueError("Invalid relevance payload")
        schema, instructions = V42_STAGES[stage]
        response = self.client.responses.create(
            model=self.model, instructions=instructions,
            input=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False,
                                                             allow_nan=False)}],
            text={"format": {"type": "json_schema", "name": stage, "strict": True,
                              "schema": schema}},
            max_output_tokens=self.max_output_tokens, store=False,
        )
        if getattr(response, "status", None) != "completed" or not getattr(response, "output_text", None):
            raise RuntimeError("Incomplete RV-042 relevance response")
        for item in getattr(response, "output", ()) or ():
            for part in getattr(item, "content", ()) or ():
                if getattr(part, "type", None) == "refusal":
                    raise RuntimeError("Provider refused relevance assessment")
        return response.output_text
