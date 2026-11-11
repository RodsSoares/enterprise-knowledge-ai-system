"""RV-042: independent veto contract for suppressed sources."""
from copy import deepcopy
import json
import pytest

from app.orchestration.v42_verification_contract import (
    validate_v42_verification, V42_VERIFICATION_SCHEMA,
)


def checked():
    return {"claims":[{"claim_index":0,"entailed":True,"relevant":True,
                       "conditions_preserved":True,"verified_citation_ids":["u1"]}],
            "materially_complete":True,"omissions":[],"decision":"PASS",
            "reason":"Grounded and within scope",
            "suppressed_requirements":[{"requirement_id":"C2","materially_needed":False,
                                        "reason":"Unasked AI workflow"}],
            "excluded_unresolved":[{"index":0,"materially_needed":False,
                                    "reason":"Unasked detail"}]}


def core():
    return {"claims":[{"text":"Policy requires approved secure transfer", "citation_ids":["u1"],
                       "requirement_ids":["C1"]}]}


def args():
    return {"answer":core(),"plan":object(),"inventory":{"facets":[],"unresolved_facets":[]},
            "suppressed_ids":["C2"],"excluded_unresolved_indices":[0]}


def validate(data=None):
    return validate_v42_verification(json.dumps(data if data is not None else checked()),**args())


def test_relevance_schema_requires_independent_reviews():
    assert "suppressed_requirements" in V42_VERIFICATION_SCHEMA["required"]
    assert "excluded_unresolved" in V42_VERIFICATION_SCHEMA["required"]


def test_positive_suppression_review_passes_including_citations():
    result=validate()
    assert result["decision"]=="PASS"


@pytest.mark.parametrize("mutation",[
    lambda x:x.pop("suppressed_requirements"),
    lambda x:x["suppressed_requirements"].clear(),
    lambda x:x["suppressed_requirements"][0].update(requirement_id="C999"),
    lambda x:x["suppressed_requirements"][0].update(materially_needed="false"),
    lambda x:x["suppressed_requirements"][0].update(reason=""),
    lambda x:x["excluded_unresolved"].clear(),
    lambda x:x["excluded_unresolved"][0].update(index=True),
    lambda x:x["excluded_unresolved"][0].update(index=7),
    lambda x:x["excluded_unresolved"][0].update(materially_needed=1),
    lambda x:x["excluded_unresolved"].append(deepcopy(x["excluded_unresolved"][0])),
    lambda x:x["claims"][0].update(verified_citation_ids=["forged"]),
])
def test_malformed_suppression_review_fails_closed(mutation):
    x=checked();mutation(x)
    with pytest.raises(ValueError):validate(x)


def test_detected_material_omission_cannot_pass():
    x=checked();x["suppressed_requirements"][0]["materially_needed"]=True
    with pytest.raises(ValueError):validate(x)


def test_detected_material_omission_can_reject_with_explicit_reason():
    x=checked();x["suppressed_requirements"][0]["materially_needed"]=True
    x.update(materially_complete=False,omissions=["A required rule was suppressed"],decision="REJECT")
    assert validate(x)["decision"]=="REJECT"


def test_verifier_can_reject_for_false_claim_without_scope_issue():
    x=checked();x["claims"][0]["entailed"]=False
    x["decision"]="REJECT"
    assert validate(x)["decision"]=="REJECT"
