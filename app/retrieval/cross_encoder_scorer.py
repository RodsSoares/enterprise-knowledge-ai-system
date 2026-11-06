"""Lazy, optional local Transformers cross-encoder for the RV-008 experiment."""

from collections.abc import Sequence
from importlib import import_module
from math import isfinite


DEFAULT_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
DEFAULT_REVISION = "1427fd652930e4ba29e8149678df786c240d8825"


class TransformersCrossEncoderScorer:
    """Score query/passage pairs locally; downloads weights on first use.

    The initial multilingual checkpoint is an experiment, not a promoted
    retrieval configuration. Raw logits are not calibrated probabilities.
    Tokenization preserves the query and truncates only the passage when the
    pair exceeds max_length. Full canonical evidence remains unchanged.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        revision: str | None = None,
        device: str = "cpu",
        batch_size: int = 8,
        max_length: int = 512,
    ) -> None:
        for name, value in (("model_name", model_name), ("device", device)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        if revision is None:
            if model_name != DEFAULT_MODEL:
                raise ValueError("Provide an explicit revision for a custom model.")
            revision = DEFAULT_REVISION
        if not isinstance(revision, str) or not revision.strip():
            raise ValueError("revision must be a non-empty string.")
        for name, value in (("batch_size", batch_size), ("max_length", max_length)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer.")
        self.model_name = model_name
        self.revision = revision
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length
        self._model = None
        self._tokenizer = None
        self._torch = None

    def load(self) -> None:
        """Load once; callers can fail early before spending on embeddings."""
        if self._model is not None:
            return
        try:
            torch = import_module("torch")
            transformers = import_module("transformers")
        except ImportError as exc:
            raise RuntimeError(
                "The local reranker requires torch and transformers. "
                "The provider-independent reranker and its tests do not."
            ) from exc
        options = {"revision": self.revision, "trust_remote_code": False}
        tokenizer = transformers.AutoTokenizer.from_pretrained(self.model_name, **options)
        model = transformers.AutoModelForSequenceClassification.from_pretrained(
            self.model_name, use_safetensors=True, **options
        )
        if model.config.num_labels != 1:
            raise ValueError("The cross-encoder must output one relevance logit per pair.")
        model.to(self.device)
        model.eval()
        self._torch, self._tokenizer, self._model = torch, tokenizer, model

    def score_pairs(self, query: str, passages: Sequence[str]) -> tuple[float, ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")
        if isinstance(passages, (str, bytes)):
            raise ValueError("passages must be a sequence of non-empty strings.")
        passages = tuple(passages)
        if any(not isinstance(text, str) or not text.strip() for text in passages):
            raise ValueError("passages must contain non-empty strings.")
        if not passages:
            return ()
        self.load()

        # Fail explicitly for a query that leaves no passage token budget.
        query_ids = self._tokenizer(query, add_special_tokens=False)["input_ids"]
        special_tokens = self._tokenizer.num_special_tokens_to_add(pair=True)
        if len(query_ids) + special_tokens >= self.max_length:
            raise ValueError("query is too long for the configured max_length.")

        scores = []
        with self._torch.inference_mode():
            for start in range(0, len(passages), self.batch_size):
                batch = passages[start : start + self.batch_size]
                features = self._tokenizer(
                    [query] * len(batch), list(batch),
                    padding=True, truncation="only_second",
                    max_length=self.max_length, return_tensors="pt",
                )
                features = {key: value.to(self.device) for key, value in features.items()}
                logits = self._model(**features).logits
                if tuple(logits.shape) != (len(batch), 1):
                    raise ValueError("Expected cross-encoder logits with shape (batch, 1).")
                values = logits[:, 0].detach().cpu().tolist()
                scores.extend(float(value) for value in values)
        if len(scores) != len(passages) or not all(isfinite(value) for value in scores):
            raise ValueError("Cross-encoder returned invalid relevance scores.")
        return tuple(scores)
