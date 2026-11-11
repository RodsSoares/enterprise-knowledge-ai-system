"""RV-038D2A: contract tests without network calls."""
import pytest

from app.scripts.rv038d2_recovery_probe import inspect_recovery


def test_invalid_budget():
    with pytest.raises(ValueError, match="budget"):
        inspect_recovery({}, {}, {}, top_k=0)


def test_unapproved_recovery():
    with pytest.raises(ValueError, match="Completed"):
        inspect_recovery(
            {}, {"status": "execution_failed"}, {}
        )


def test_recovery_not_requested():
    with pytest.raises(ValueError, match="not requested"):
        inspect_recovery(
            {},
            {
                "status": "assessment_recorded",
                "decision": {"decision": "APPROVE"},
            },
            {},
        )
