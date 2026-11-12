"""Minimal password gate for a private MVP demo (not enterprise identity management)."""
import hmac

MIN_PASSWORD_LENGTH = 16


def password_is_configured(secret: str) -> bool:
    return isinstance(secret, str) and len(secret) >= MIN_PASSWORD_LENGTH


def password_matches(provided: str, configured: str) -> bool:
    """Never grant access when the deployment secret is unset or too short."""
    if not password_is_configured(configured) or not isinstance(provided, str):
        return False
    return hmac.compare_digest(provided.encode("utf-8"), configured.encode("utf-8"))
