"""RV-039A: experimental rank fusion with a protected vector prefix.

Pure selection policy. Does not fetch sources, call models, modify snapshots,
or make semantic claims. Prefix protects UNITS, not unique documents.
"""
from dataclasses import dataclass
from collections.abc import Mapping

from app.retrieval.lexical_index import tokenize


# Versioned, generic domain vocabulary; not tuned to a Golden Set answer.
BILINGUAL_GLOSSARY_V1 = {
    "política": ("policy",), "corporativa": ("corporate",),
    "compartilhamento": ("sharing",), "compartilhar": ("share",),
    "externo": ("external",), "externa": ("external",),
    "fornecedor": ("supplier",), "fornecedores": ("suppliers",),
    "dados": ("data",), "exceções": ("exceptions",),
    "exceção": ("exception",), "justificativa": ("justification",),
    "negócio": ("business",), "documentada": ("documented",),
    "documentado": ("documented",), "aprovação": ("approval",),
    "aprovações": ("approvals",), "controles": ("controls",),
    "segurança": ("security",), "autoridade": ("authority",),
    "procedimento": ("procedure",), "operacional": ("operational",),
    "transportadora": ("carrier",), "transportadoras": ("carriers",),
    "incidente": ("incident",), "incidentes": ("incidents",),
    "contrato": ("contract",), "contratado": ("contracted",),
    "prazo": ("deadline",), "aprovado": ("approved",),
    "aprovada": ("approved",),
}


def controlled_bilingual_query(query: str) -> str:
    """Append limited lexical aliases; leave original query and negation intact."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Nonempty query required")
    seen = set(tokenize(query))
    extras = []
    for term in tokenize(query):
        for alias in BILINGUAL_GLOSSARY_V1.get(term, ()):
            if alias not in seen:
                extras.append(alias)
                seen.add(alias)
    return query + (" " + " ".join(extras) if extras else "")


def _field(hit, key):
    return hit[key] if isinstance(hit, Mapping) else getattr(hit, key)


def _validated(hits, label):
    if not isinstance(hits, (tuple, list)):
        raise ValueError(f"{label} hits must be a sequence")
    ids = []
    for expected_rank, hit in enumerate(hits, 1):
        uid, rank = _field(hit, "chunk_id"), _field(hit, "rank")
        if not isinstance(uid, str) or not uid.strip() or type(rank) is not int or rank != expected_rank:
            raise ValueError(f"Invalid {label} hit identity/rank")
        ids.append(uid)
    if len(set(ids)) != len(ids):
        raise ValueError(f"Duplicated {label} hits")
    return ids


@dataclass(frozen=True)
class FusionPolicy:
    protected_vector_units: int = 3
    rrf_k: int = 60
    lexical_weight: float = 1.0

    def __post_init__(self):
        if (type(self.protected_vector_units) is not int or self.protected_vector_units < 0
                or type(self.rrf_k) is not int or self.rrf_k < 1
                or type(self.lexical_weight) not in (int, float)
                or not 0 <= self.lexical_weight <= 2):
            raise ValueError("Invalid fusion policy")


def fuse_ranked(vector_hits, lexical_hits, *, top_k: int, policy=None):
    """Deterministic vector-prefix + RRF candidate selection.

    Returns selected IDs and transparent trace. Does not impose a doc quota.
    With zero lexical matches, vector ranks are preserved exactly.
    """
    policy = policy or FusionPolicy()
    if type(top_k) is not int or top_k < 1:
        raise ValueError("Positive top_k required")
    vector = _validated(vector_hits, "vector")
    lexical = _validated(lexical_hits, "lexical")
    if not vector and not lexical:
        return (), {"policy": "vector_prefix_rrf/1", "protected": [], "lexical_used": False, "ranked": []}
    protected = vector[:min(policy.protected_vector_units, top_k)]
    if not lexical or policy.lexical_weight == 0:
        ranked = vector[:top_k]
        return tuple(ranked), {"policy": "vector_prefix_rrf/1", "protected": protected,
                               "lexical_used": False, "ranked": ranked}
    scores, insertion = {}, {}
    for channel, weight in ((vector, 1.0), (lexical, policy.lexical_weight)):
        for rank, uid in enumerate(channel, 1):
            insertion.setdefault(uid, len(insertion))
            scores[uid] = scores.get(uid, 0.0) + weight / (policy.rrf_k + rank)
    remainder = sorted(scores, key=lambda uid: (-scores[uid], insertion[uid]))
    selected = list(protected)
    for uid in remainder:
        if len(selected) >= top_k:
            break
        if uid not in selected:
            selected.append(uid)
    return tuple(selected), {"policy": "vector_prefix_rrf/1", "protected": protected,
                             "lexical_used": True, "ranked": selected,
                             "scores": [{"unit_id": uid, "rrf_score": scores[uid]}
                                        for uid in selected]}
