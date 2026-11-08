"""Hybrid retrieval for versioned units, without document-diversity quotas."""
from dataclasses import asdict
import math

from app.chunking.evidence_units import digest
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_query_filter import FILTER_VERSION, filter_lexical_query
from app.retrieval.vector_index import NumPyVectorIndex


def cache_key(units, model):
    return digest(dict(model=model, texts=[dict(unit_id=u.unit_id, text=u.search_text)
                                          for u in units if u.searchable]))


def check_vectors(vectors, count):
    if not isinstance(vectors, (list, tuple)) or len(vectors) != count or not count:
        raise ValueError("Embedding count mismatch")
    dimensions = set()
    for row in vectors:
        if not isinstance(row, (list, tuple)) or not row:
            raise ValueError("Empty embedding")
        dimensions.add(len(row))
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in row):
            raise ValueError("Nonfinite embedding")
        if not any(v != 0 for v in row):
            raise ValueError("Zero embedding")
    if len(dimensions) != 1:
        raise ValueError("Embedding dimensions differ")


def make_cache(units, model, vectors):
    selected = tuple(u for u in units if u.searchable)
    check_vectors(vectors, len(selected))
    body = dict(version="unit-embeddings/1", key=cache_key(units, model), model=model,
                unit_ids=[u.unit_id for u in selected], vectors=vectors)
    return dict(hash=digest(body), cache=body)


def read_cache(payload, units, model):
    body = payload["cache"]
    if (set(payload) != {"hash", "cache"} or body["version"] != "unit-embeddings/1"
            or payload["hash"] != digest(body) or body["key"] != cache_key(units, model)
            or body["model"] != model
            or body["unit_ids"] != [u.unit_id for u in units if u.searchable]):
        raise ValueError("Embedding cache differs from model/units/text; use a new cache path")
    check_vectors(body["vectors"], len(body["unit_ids"]))
    return body["vectors"]


class EvidenceUnitRetriever:
    def __init__(self, units, vectors, embedding_provider):
        self.units = tuple(u for u in units if u.searchable)
        check_vectors(vectors, len(self.units))
        self.vectors = dict(zip((u.unit_id for u in self.units), vectors))
        self.embedding_provider = embedding_provider
        self.query_cache = {}

    def search(self, query, document_ids=(), top_k=20):
        if not query.strip() or type(top_k) is not int or top_k < 1:
            raise ValueError("Nonempty query and positive top_k required")
        eligible = tuple(u for u in self.units if not document_ids or u.document_id in document_ids)
        if not eligible:
            return (), dict(vector=[], lexical=[], fused=[])
        if query not in self.query_cache:
            vector = self.embedding_provider.embed_query(query)
            check_vectors([vector], 1)
            self.query_cache[query] = vector
        ids = tuple(u.unit_id for u in eligible)
        index = NumPyVectorIndex()
        index.add(ids, tuple(self.vectors[i] for i in ids))
        lexical = BM25LexicalIndex()
        lexical.add(ids, [u.search_text for u in eligible])
        vector_hits = index.search(self.query_cache[query], top_k=top_k)
        lexical_query = filter_lexical_query(query)
        lexical_hits = lexical.search(lexical_query, top_k=top_k) if lexical_query else ()
        scores, order = {}, {}
        for hits in (vector_hits, lexical_hits):
            for h in hits:
                order.setdefault(h.chunk_id, len(order))
                scores[h.chunk_id] = scores.get(h.chunk_id, 0) + 1 / (60 + h.rank)
        ranked = sorted(scores, key=lambda uid: (-scores[uid], order[uid]))[:top_k]
        catalog = {u.unit_id: u for u in eligible}
        trace = dict(lexical_query=lexical_query, lexical_filter=FILTER_VERSION,
                     vector=[asdict(h) for h in vector_hits], lexical=[asdict(h) for h in lexical_hits],
                     fused=[dict(unit_id=uid, score=scores[uid], rank=i+1) for i, uid in enumerate(ranked)])
        return tuple(catalog[uid] for uid in ranked), trace
