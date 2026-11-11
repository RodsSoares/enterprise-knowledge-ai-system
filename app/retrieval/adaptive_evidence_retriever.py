"""RV-039A opt-in drop-in for EvidencePlanner.retriever.

This class deliberately does not replace EvidenceUnitRetriever in the baseline
pipeline until offline and live comparisons justify promotion.
"""
from dataclasses import asdict

from app.retrieval.adaptive_fusion import FusionPolicy, fuse_ranked, controlled_bilingual_query
from app.retrieval.evidence_unit_retriever import EvidenceUnitRetriever, check_vectors
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_query_filter import FILTER_VERSION, filter_lexical_query
from app.retrieval.vector_index import NumPyVectorIndex


class AdaptiveEvidenceUnitRetriever(EvidenceUnitRetriever):
    def __init__(self, units, vectors, embedding_provider, *, policy=None,
                 lexical_query_fn=controlled_bilingual_query):
        super().__init__(units, vectors, embedding_provider)
        self.policy = policy or FusionPolicy()
        if not callable(lexical_query_fn):
            raise TypeError("lexical_query_fn must be callable")
        self.lexical_query_fn = lexical_query_fn

    def search(self, query, document_ids=(), top_k=20):
        if not isinstance(query, str) or not query.strip() or type(top_k) is not int or top_k < 1:
            raise ValueError("Nonempty query and positive top_k required")
        if not isinstance(document_ids, (tuple, list)) or any(
            not isinstance(x, str) or not x for x in document_ids
        ):
            raise ValueError("Invalid document scope")
        eligible = tuple(u for u in self.units if not document_ids or u.document_id in document_ids)
        if not eligible:
            return (), dict(vector=[], lexical=[], fused=[], policy="vector_prefix_rrf/1")
        if query not in self.query_cache:
            vector = self.embedding_provider.embed_query(query)
            check_vectors([vector], 1)
            self.query_cache[query] = vector
        ids = tuple(u.unit_id for u in eligible)
        vector_index = NumPyVectorIndex()
        vector_index.add(ids, tuple(self.vectors[uid] for uid in ids))
        vector_hits = vector_index.search(self.query_cache[query], top_k=top_k)
        lexical_source = self.lexical_query_fn(query)
        if not isinstance(lexical_source, str) or not lexical_source.strip():
            raise ValueError("Invalid lexical query")
        lexical_query = filter_lexical_query(lexical_source)
        lexical_hits = ()
        if lexical_query:
            lexical_index = BM25LexicalIndex()
            lexical_index.add(ids, [u.search_text for u in eligible])
            lexical_hits = lexical_index.search(lexical_query, top_k=top_k)
        selected, fusion = fuse_ranked(vector_hits, lexical_hits, top_k=top_k, policy=self.policy)
        catalog = {u.unit_id: u for u in eligible}
        trace = {
            "vector": [asdict(h) for h in vector_hits],
            "lexical": [asdict(h) for h in lexical_hits],
            "lexical_query": lexical_query,
            "lexical_filter": FILTER_VERSION,
            "fusion": fusion,
            "fused": [{"unit_id": uid, "rank": i + 1} for i, uid in enumerate(selected)],
            "retrieval_version": "adaptive-evidence/1",
        }
        return tuple(catalog[uid] for uid in selected), trace
