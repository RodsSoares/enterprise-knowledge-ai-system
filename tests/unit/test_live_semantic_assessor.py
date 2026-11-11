"""RV-038C2A: mocked API, no network."""
import json
from types import SimpleNamespace

import pytest

from app.orchestration.live_provider import (
    BudgetedClient, RunBudget,
)
from app.orchestration.live_semantic_assessor import (
    LiveSemanticAssessor, SemanticProviderError,
    ASSURANCE_SCHEMA,
)


def payload():
    return {
        "assurance_request": {
            "schema_version": "0.1",
            "question_hash": "hash",
            "snapshot_id": "snapshot",
            "evidence_set_hash": "evidence",
            "requirement_ids": ["C1"],
            "candidate_chunk_ids": ["u1"],
            "recovery_used": False,
        },
        "canonical_evidence": [{
            "unit_id": "u1",
            "reading_text": "Approved policy.",
        }],
        "requirements": [{
            "requirement_id": "C1",
            "description": "Approval policy",
        }],
    }


class FakeSDK:
    def __init__(self, *, status="completed", output=None):
        self.status = status
        self.output = output
        self.calls = []
        self.responses = SimpleNamespace(create=self.create)

    def with_options(self, **kwargs):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            status=self.status,
            output_text=self.output,
            output=[],
            id="fake-response",
            model="test-model",
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=50,
            ),
        )


def client(sdk, max_calls=1):
    return BudgetedClient(
        sdk,
        RunBudget(
            max_input_tokens=100000,
            max_output_tokens=4000,
            max_calls=max_calls,
            deadline_seconds=120,
            max_cost_usd="1.00",
        ),
        {
            "test-model": {
                "input_per_million": "1",
                "output_per_million": "4",
            }
        },
    )


def test_live_provider_uses_strict_schema():
    sdk = FakeSDK(output='{"decision":"APPROVE"}')
    budget = client(sdk)
    provider = LiveSemanticAssessor(
        budget, "test-model", 1200
    )

    assert provider.invoke("assurance", payload())
    call = sdk.calls[0]
    fmt = call["text"]["format"]
    assert fmt["strict"] is True
    assert fmt["schema"] == ASSURANCE_SCHEMA
    assert call["store"] is False
    assert call["max_output_tokens"] == 1200
    assert budget.report()["calls"] == 1


def test_second_call_blocked_by_budget():
    sdk = FakeSDK(output='{"decision":"APPROVE"}')
    provider = LiveSemanticAssessor(
        client(sdk), "test-model"
    )
    provider.invoke("assurance", payload())

    from app.orchestration.coordinator import BudgetExceeded
    with pytest.raises(BudgetExceeded):
        provider.invoke("assurance", payload())
    assert len(sdk.calls) == 1


def test_incomplete_response_rejected():
    sdk = FakeSDK(status="incomplete", output=None)
    provider = LiveSemanticAssessor(
        client(sdk), "test-model"
    )
    with pytest.raises(
        SemanticProviderError, match="Incomplete"
    ):
        provider.invoke("assurance", payload())


def test_bad_stage_rejected_without_call():
    sdk = FakeSDK(output="{}")
    provider = LiveSemanticAssessor(
        client(sdk), "test-model"
    )
    with pytest.raises(
        SemanticProviderError, match="stage"
    ):
        provider.invoke("generation", payload())
    assert sdk.calls == []


def test_budget_client_required():
    with pytest.raises(TypeError):
        LiveSemanticAssessor(
            object(), "test-model"
        )


def test_invalid_token_cap_rejected():
    sdk = FakeSDK(output="{}")
    with pytest.raises(ValueError):
        LiveSemanticAssessor(
            client(sdk), "test-model", 0
        )
