import json
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from app.generation.answer_contract import request_id_for
from app.scripts.compare_saved_generation import compare, restore_context, main
from tests.unit.test_rag_service import service, reply


def saved_result():
    return service().ask("Quais regras se aplicam?").to_dict()


def test_restore_preserves_exact_generation_context():
    saved = saved_result()
    question, context = restore_context(saved)
    assert context.text == saved["context"]["text"]
    assert context.citations == saved["context"]["citations"]
    assert request_id_for(question, context) == saved["answer"]["request_id"]


@pytest.mark.parametrize("change", ["question", "text", "citation"])
def test_restore_rejects_mismatched_evidence(change):
    saved = saved_result()
    if change == "question": saved["question"] = "Other question"
    elif change == "text": saved["context"]["text"] = saved["context"]["text"].replace("Regra", "Alterado")
    else: saved["context"]["citations"]["E1"]["document_id"] = "OTHER"
    with pytest.raises(ValueError): restore_context(saved)


def test_comparison_changes_only_instructions_and_makes_no_embedding_calls():
    question, context = restore_context(saved_result())
    client = Mock()
    client.responses.create.return_value = NS(status="completed", output=[],
        output_text=reply(question, context), model="pinned-model", id="response-id", usage=None)
    rows = list(compare(client, "pinned-model", question, context))
    assert [r["status"] for r in rows] == ["CONTRACT_VALID", "CONTRACT_VALID"]
    calls = [dict(c.kwargs) for c in client.responses.create.call_args_list]
    assert calls[0].pop("instructions") != calls[1].pop("instructions")
    assert calls[0] == calls[1]
    client.embeddings.create.assert_not_called()


def test_failure_remains_error_and_second_arm_is_preserved():
    question, context = restore_context(saved_result())
    client = Mock()
    client.responses.create.side_effect = [TimeoutError(), NS(status="completed", output=[],
        output_text=reply(question, context), model="pinned-model", id="r2", usage=None)]
    rows = list(compare(client, "pinned-model", question, context))
    assert rows[0]["status"] == "ERROR" and rows[0]["error_type"] == "TimeoutError"
    assert rows[1]["status"] == "CONTRACT_VALID"


def test_existing_output_not_overwritten(tmp_path):
    output = tmp_path / "out.json"
    output.write_text("existing")
    with pytest.raises(SystemExit): main(["--source", "unused.json", "--output", str(output)])
    assert output.read_text() == "existing"
