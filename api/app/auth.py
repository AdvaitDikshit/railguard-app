"""
Minimal admin auth — a single shared token, checked via header, gating
only the human-verification endpoint (POST /reports/{id}/verify).

This is intentionally the smallest thing that closes the gap: it's not
a user-account system (public anonymous reporting stays open, by
design — see the original audit's UX reasoning), just a lock on the
one write path that records an engineering sign-off.
"""

from fastapi import Header, HTTPException

from .config import settings


def require_admin(x_admin_token: str = Header(default="")) -> None:
    if not settings.admin_token:
        # Fail closed: an unconfigured deployment must not silently allow
        # anyone to write engineering verifications.
        raise HTTPException(
            status_code=503,
            detail="Admin verification is not configured on this server (ADMIN_TOKEN unset).",
        )
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token.")
