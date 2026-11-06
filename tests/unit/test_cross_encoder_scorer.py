"""Test the optional model adapter at its external boundary, without downloads."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.retrieval.cross_encoder_scorer import (
    DEFAULT_MODEL, DEFAULT_REVISION, TransformersCrossEncoderScorer,
)


def fake_runtime(batch_scores):
    model = Mock()
    model.config.num_labels = 1
    outputs = []
    for values in batch_scores:
        logits = MagicMock()
        logits.shape = (len(values), 1)
        logits.__getitem__.return_value.detach.return_value.cpu.return_value.tolist.return_value = values
        outputs.append(SimpleNamespace(logits=logits))
    model.side_effect = outputs
    tensor = Mock()
    tensor.to.return_value = tensor
    tokenizer = Mock(side_effect=lambda *args, **kwargs:
                     {"input_ids": [1, 2]} if kwargs.get("add_special_tokens") is False
                     else {"input_ids": tensor})
    tokenizer.num_special_tokens_to_add.return_value = 4
    transformers = SimpleNamespace(
        AutoTokenizer=Mock(from_pretrained=Mock(return_value=tokenizer)),
        AutoModelForSequenceClassification=Mock(from_pretrained=Mock(return_value=model)),
    )
    torch = SimpleNamespace(inference_mode=Mock(side_effect=nullcontext))
    return {"torch": torch, "transformers": transformers}, tokenizer, model, tensor


def test_lazy_loading_pinned_revision_batch_order_and_local_inference():
    runtime, tokenizer, model, tensor = fake_runtime([[3.0, -1.0], [7.0]])
    with patch("app.retrieval.cross_encoder_scorer.import_module", side_effect=runtime.__getitem__) as importer:
        scorer = TransformersCrossEncoderScorer(batch_size=2, max_length=128)
        importer.assert_not_called()
        assert scorer.score_pairs("query", []) == ()
        importer.assert_not_called()
        assert scorer.score_pairs("query", ["first", "second", "third"]) == (3, -1, 7)
        scorer.load()
        assert importer.call_count == 2
    runtime["transformers"].AutoModelForSequenceClassification.from_pretrained.assert_called_once_with(
        DEFAULT_MODEL, use_safetensors=True, revision=DEFAULT_REVISION, trust_remote_code=False
    )
    runtime["transformers"].AutoTokenizer.from_pretrained.assert_called_once_with(
        DEFAULT_MODEL, revision=DEFAULT_REVISION, trust_remote_code=False
    )
    model.to.assert_called_once_with("cpu")
    model.eval.assert_called_once()
    assert model.call_count == 2
    pair_calls = tokenizer.call_args_list[1:]
    assert pair_calls[0].args == (["query", "query"], ["first", "second"])
    assert pair_calls[1].args == (["query"], ["third"])
    assert pair_calls[0].kwargs == dict(padding=True, truncation="only_second", max_length=128, return_tensors="pt")
    tensor.to.assert_called_with("cpu")


@pytest.mark.parametrize("options", [
    {"batch_size": 0}, {"batch_size": True}, {"max_length": 1.2},
    {"max_length": -1}, {"model_name": ""}, {"revision": ""},
    {"device": " "}, {"model_name": "custom/model"},
])
def test_invalid_configuration_rejected_without_loading(options):
    with patch("app.retrieval.cross_encoder_scorer.import_module") as importer:
        with pytest.raises(ValueError):
            TransformersCrossEncoderScorer(**options)
        importer.assert_not_called()


@pytest.mark.parametrize("query,passages", [("", ["x"]), (None, []),
    ("q", "single string"), ("q", [""]), ("q", [None])])
def test_invalid_pair_inputs_rejected_before_loading(query, passages):
    scorer = TransformersCrossEncoderScorer()
    with patch.object(scorer, "load") as load:
        with pytest.raises(ValueError):
            scorer.score_pairs(query, passages)
        load.assert_not_called()


def test_missing_optional_dependency_reports_actionable_error():
    with patch("app.retrieval.cross_encoder_scorer.import_module", side_effect=ModuleNotFoundError("torch")):
        with pytest.raises(RuntimeError, match="torch and transformers"):
            TransformersCrossEncoderScorer().load()


def test_multiclass_model_rejected():
    runtime, _, model, _ = fake_runtime([])
    model.config.num_labels = 2
    with patch("app.retrieval.cross_encoder_scorer.import_module", side_effect=runtime.__getitem__):
        with pytest.raises(ValueError, match="one relevance logit"):
            TransformersCrossEncoderScorer().load()


def test_oversized_query_fails_explicitly_instead_of_dropping_query_text():
    runtime, _, model, _ = fake_runtime([])
    with patch("app.retrieval.cross_encoder_scorer.import_module", side_effect=runtime.__getitem__):
        with pytest.raises(ValueError, match="query is too long"):
            TransformersCrossEncoderScorer(max_length=6).score_pairs("query", ["passage"])
    model.assert_not_called()


@pytest.mark.parametrize("scores", [[float("nan")], [float("inf")]])
def test_nonfinite_logits_rejected(scores):
    runtime, _, _, _ = fake_runtime([scores])
    with patch("app.retrieval.cross_encoder_scorer.import_module", side_effect=runtime.__getitem__):
        with pytest.raises(ValueError, match="invalid relevance"):
            TransformersCrossEncoderScorer().score_pairs("query", ["passage"])


def test_wrong_output_shape_rejected():
    runtime, _, model, _ = fake_runtime([])
    model.side_effect = None
    model.return_value.logits.shape = (1, 2)
    with patch("app.retrieval.cross_encoder_scorer.import_module", side_effect=runtime.__getitem__):
        with pytest.raises(ValueError, match="shape"):
            TransformersCrossEncoderScorer().score_pairs("query", ["passage"])


def test_download_failure_is_visible_and_does_not_mark_provider_loaded():
    runtime, _, _, _ = fake_runtime([])
    runtime["transformers"].AutoTokenizer.from_pretrained.side_effect = OSError("download failed")
    scorer = TransformersCrossEncoderScorer()
    with patch("app.retrieval.cross_encoder_scorer.import_module", side_effect=runtime.__getitem__):
        with pytest.raises(OSError, match="download failed"):
            scorer.load()
    assert scorer._model is None
