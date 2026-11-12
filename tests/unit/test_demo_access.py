"""Deployment access gate must fail closed before any model request."""
from app.frontend.access import password_is_configured, password_matches


def test_empty_and_short_deployment_secrets_are_rejected():
    assert not password_is_configured("")
    assert not password_is_configured("short")
    assert not password_matches("", "")
    assert not password_matches("short", "short")


def test_comparison_rejects_wrong_password_and_accepts_exact_match():
    password = "long-private-demo-password"
    assert password_is_configured(password)
    assert not password_matches("wrong-password-123", password)
    assert password_matches(password, password)
    assert not password_matches(password + " ", password)
