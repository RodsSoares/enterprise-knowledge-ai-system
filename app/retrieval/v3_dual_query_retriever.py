"""Explicit semantic/lexical query projections for a SINGLE authorized snapshot.

Initial discovery stays on RV-039 AdaptiveEvidenceUnitRetriever.search().
Recovery uses embedding query and BM25 query separately, without injecting source IDs.
"""
from dataclasses import asdict

from app.retrieval.adaptive_evidence_retriever import AdaptiveEvidenceUnitRetriever
from app.retrieval.adaptive_fusion import fuse_ranked
from app.retrieval.evidence_unit_retriever import check_vectors
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_query_filter import filter_lexical_query
from app.retrieval.vector_index import NumPyVectorIndex


class DualQueryEvidenceRetriever(AdaptiveEvidenceUnitRetriever):
    def search_projections(self, semantic_query, lexical_query, document_ids=(), top_k=20):
        if (not isinstance(semantic_query, str) or not semantic_query.strip()
                or not isinstance(lexical_query, str) or not lexical_query.strip()
                or not isinstance(document_ids, (tuple, list))
                or any(not isinstance(d, str) or not d for d in document_ids)
                or type(top_k) is not int or not 1 <= top_k <= 40):
            raise ValueError("Invalid bounded dual-query request")
        eligible = tuple(u for u in self.units if not document_ids or u.document_id in document_ids)
        if not eligible:
            return (), {"version": "dual-query/1", "vector": [], "lexical": [], "fused": []}
        if semantic_query not in self.query_cache:
            vector = self.embedding_provider.embed_query(semantic_query)
            check_vectors([vector], 1)
            self.query_cache[semantic_query] = vector
        ids = tuple(u.unit_id for u in eligible)
        vector_index = NumPyVectorIndex()
        vector_index.add(ids, tuple(self.vectors[i] for i in ids))
        vector_hits = vector_index.search(self.query_cache[semantic_query], top_k)
        filtered = filter_lexical_query(lexical_query)
        lexical_hits = ()
        if filtered:
            lexical_index = BM25LexicalIndex()
            lexical_index.add(ids, [u.search_text for u in eligible])
            lexical_hits = lexical_index.search(filtered, top_k)
        selected, fusion = fuse_ranked(vector_hits, lexical_hits, top_k=top_k, policy=self.policy)
        catalog = {u.unit_id: u for u in eligible}
        return tuple(catalog[i] for i in selected), {
            "version": "dual-query/1", "semantic_query": semantic_query,
            "lexical_query": filtered, "document_ids": list(document_ids),
            "vector": [asdict(h) for h in vector_hits],
            "lexical": [asdict(h) for h in lexical_hits],
            "fusion": fusion, "fused": list(selected),
        }
