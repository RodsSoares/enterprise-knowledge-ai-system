"""Runner checkpoints and persistent cache, with a fake SDK and no paid calls."""
import json
from types import SimpleNamespace as NS

import pytest

from app.chunking.evidence_units import EvidenceUnitBuilder
from app.ingestion.schemas import NormalizedContent, TextBlock
from app.scripts import plan_evidence_units as runner


@pytest.fixture
def setup(tmp_path, monkeypatch):
    units = EvidenceUnitBuilder().build(NormalizedContent((TextBlock("p", 0, "paragraph",
        "Confidential data requires a secure channel."),)), document_id="DOC-005",
        title="Sharing", source_revision="a"*64)
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps(dict(snapshot_id="s", snapshot=dict(documents=[]))))
    config = tmp_path / "config.json"
    config.write_text(json.dumps(dict(models=dict(assessment="fake", generation="fake", embedding="embed"),
        prices={m:dict(input_per_million="0.01", output_per_million="0.01") for m in ("fake","embed")},
        budget=dict(max_input_tokens=200000,max_output_tokens=20000,max_calls=7,
                    deadline_seconds=180,max_cost_usd="1"),assessment_output_tokens=4000,
        generation_output_tokens=2000,as_of="2026-11-07")))
    # Snapshot integrity is tested separately; this test isolates CLI/SDK orchestration.
    monkeypatch.setattr(runner, "verify_snapshot", lambda *a, **kw: units)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-not-used-on-network")
    calls = []
    class SDK:
        def __init__(self, **kwargs):
            self.responses = NS(create=self.response)
            self.embeddings = NS(create=self.embedding)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def with_options(self, **kwargs): return self
        def embedding(self, **kwargs):
            calls.append("documents" if isinstance(kwargs["input"], list) else "query")
            n = len(kwargs["input"]) if isinstance(kwargs["input"], list) else 1
            return NS(data=[NS(index=i, embedding=[1.,0.]) for i in range(n)],
                      usage=NS(prompt_tokens=10), id="embedding", model="embed")
        def response(self, **kwargs):
            payload = json.loads(kwargs["input"][0]["content"])
            if kwargs["text"]["format"]["name"] == "evidence_scope":
                calls.append("scope")
                assert set(payload) == {"question"}
                answer = dict(request_kind="general", focus="sharing", known_conditions=[],
                    exclusions=[], unknown_conditions=[], decision="proceed", clarification=None)
            else:
                calls.append("plan")
                unit = payload["candidates"][0]
                answer = dict(items=[dict(need="Channel", use="category", condition="Confidential",
                    scope_link=dict(question_quote="compartilhar", explanation="Control for the requested sharing action."),
                    supports=[dict(unit_id=unit["unit_id"],quote=unit["reading_text"])])],
                    action=dict(kind="complete"))
            return NS(status="completed",output_text=json.dumps(answer),output=[],id="response",
                      model="fake",usage=NS(input_tokens=100,output_tokens=100))
    import openai
    monkeypatch.setattr(openai,"OpenAI",SDK)
    base = ["--snapshot",str(snapshot),"--config",str(config),"--question","Como compartilhar?",
            "--embedding-cache",str(tmp_path/"cache.json")]
    return base,calls,tmp_path


def test_dry_run_never_calls_sdk_or_creates_cache(setup):
    base,calls,path = setup
    assert runner.main([*base,"--output",str(path/"plan.json")]) == 0
    assert not calls and not (path/"cache.json").exists()
    assert json.loads((path/"plan.json").read_text())["status"] == "dry_run"


def test_live_runner_saves_bundle_ledger_and_reuses_document_embeddings(setup):
    base,calls,path = setup
    for name in ("first.json","second.json"):
        assert runner.main([*base,"--output",str(path/name),"--execute"]) == 0
    assert calls == ["documents","scope","query","plan","scope","query","plan"]
    report = json.loads((path/"second.json").read_text())
    assert report["status"] == "planned_pending_review"
    assert report["usage"]["calls"] == 3 and report["result"]["bundle"]


def test_existing_output_is_not_overwritten(setup):
    base,calls,path = setup
    output = path/"existing.json"
    output.write_text("preserve")
    with pytest.raises(SystemExit): runner.main([*base,"--output",str(output),"--execute"])
    assert output.read_text() == "preserve" and not calls


def replay_args(base, path, source="first.json", output="replay.json"):
    return ["--snapshot", base[1], "--config", base[3],
            "--replay-source", str(path/source), "--output", str(path/output)]


def test_replay_calls_only_planner_and_preserves_request(setup):
    base,calls,path = setup
    runner.main([*base,"--output",str(path/"first.json"),"--execute"])
    original = json.loads((path/"first.json").read_text())
    calls.clear()
    args = replay_args(base,path)
    assert runner.main([*args,"--execute"]) == 0
    result = json.loads((path/"replay.json").read_text())
    assert calls == ["plan"] and result["usage"]["calls"] == 1
    assert result["execution_budget"]["max_calls"] == 1
    assert result["embedding_cache"] == "not_used"
    before = next(e["payload"] for e in original["result"]["trace"] if e["stage"]=="plan_request")
    after = next(e["payload"] for e in result["result"]["trace"] if e["stage"]=="plan_request")
    assert before == after


def test_replay_dry_run_has_no_sdk_calls(setup):
    base,calls,path = setup
    runner.main([*base,"--output",str(path/"first.json"),"--execute"])
    calls.clear()
    assert runner.main(replay_args(base,path)) == 0
    assert not calls
    assert json.loads((path/"replay.json").read_text())["expected_calls"] == dict(normal=1,maximum=1)


@pytest.mark.parametrize("change", ["text", "scope", "model"])
def test_replay_rejects_modified_inputs_before_any_payment(setup, change):
    base,calls,path = setup
    runner.main([*base,"--output",str(path/"first.json"),"--execute"])
    calls.clear()
    data = json.loads((path/"first.json").read_text())
    request = next(e["payload"] for e in data["result"]["trace"] if e["stage"]=="plan_request")
    if change == "text": request["candidates"][0]["reading_text"] = "Tampered"
    if change == "scope": request["scope"]["focus"] = "Different task"
    if change == "model": data["config"]["models"]["assessment"] = "other"
    (path/"first.json").write_text(json.dumps(data))
    with pytest.raises(SystemExit): runner.main([*replay_args(base,path),"--execute"])
    assert not calls and not (path/"replay.json").exists()


def test_replay_records_lookup_without_executing_it(setup, monkeypatch):
    base,calls,path = setup
    runner.main([*base,"--output",str(path/"first.json"),"--execute"])
    class Provider:
        def invoke(self, stage, payload):
            assert stage == "plan"
            return json.dumps(dict(items=[], action=dict(kind="search",query="additional",gap="rule")))
    monkeypatch.setattr(runner,"LivePlanningProvider",lambda *a: Provider())
    calls.clear()
    assert runner.main([*replay_args(base,path),"--execute"]) == 0
    data=json.loads((path/"replay.json").read_text())
    assert data["status"] == "replay_requires_lookup" and not calls
