"""Security layer mapped to the OWASP Top 10 (2021).

WHY THIS FILE EXISTS
--------------------
The team asked for the OWASP Top 10 to guide the app's security. This module collects the
concrete, prototype-appropriate controls in one readable place, each tagged with the OWASP
category it addresses, so the mapping is explicit and defensible when pitching.

OWASP TOP 10 (2021) -> what we do here
--------------------------------------
A01 Broken Access Control    No hidden admin routes; the API is read/compute only and holds
                             no user accounts or private records to access.
A02 Cryptographic Failures   We persist NO user data server-side (scan history lives only in
                             the user's browser), so there are no secrets/PII at rest to leak.
A03 Injection                All inputs validated by Pydantic + explicit size/type caps; no
                             SQL, no shell, no eval. Uploaded files are parsed, never executed.
A04 Insecure Design          Privacy-by-design: the server is stateless; nothing to breach.
A05 Security Misconfiguration Locked-down CORS allow-list, no wildcard; security headers on
                             every response; API docs can be disabled in production.
A06 Vulnerable Components     Pinned dependency versions in requirements.txt.
A07 Auth Failures            No auth surface to break (no login) - deliberate for a prototype.
A08 Integrity Failures       Upload size/extension limits; CSP blocks unexpected script origins.
A09 Logging/Monitoring       Errors are sanitised (no stack traces to clients); requests counted
                             for basic rate-limit visibility.
A10 SSRF                     The outbound "check-link" fetch was REMOVED - the only SSRF vector
                             is gone. The app makes no server-side outbound requests.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

# ---- Request-body cap for JSON scans (A03) ----
MAX_JSON_BODY_BYTES = 256 * 1024            # 256 KB

# ---- Rate limiting (A09, basic abuse resistance) ----
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 120               # per client IP per window

# ---- CORS allow-list (A05). Override with env for a real deployment. ----
def allowed_origins() -> list[str]:
    raw = os.environ.get("DEINFLUENCE_ALLOWED_ORIGINS", "")
    if raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    # Safe local defaults for the prototype/demo.
    return [
        "http://localhost:8000", "http://127.0.0.1:8000",
        "http://localhost:8080", "http://127.0.0.1:8080",
    ]


# Content-Security-Policy kept strict but compatible with our inline dashboard styles/scripts.
# 'self' for scripts/styles; no third-party script origins (A05/A08). connect-src 'self' so
# the page can only call its own API. frame-ancestors 'none' blocks clickjacking.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "manifest-src 'self'; "
    "worker-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

SECURITY_HEADERS: Dict[str, str] = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardening headers to every response (A05 Security Misconfiguration)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """A small in-memory sliding-window limiter per client IP (A09 / abuse resistance).

    This is intentionally simple and process-local - enough to blunt accidental floods in a
    demo. A real deployment would use a shared store (e.g. Redis) behind a load balancer.
    """

    def __init__(self, app):
        super().__init__(app)
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        # Only meter the compute/API endpoints; static assets are cheap and cached.
        if request.url.path.startswith("/api/"):
            client = request.client.host if request.client else "unknown"
            now = time.monotonic()
            window = self._hits[client]
            while window and now - window[0] > RATE_LIMIT_WINDOW_SECONDS:
                window.popleft()
            if len(window) >= RATE_LIMIT_MAX_REQUESTS:
                raise HTTPException(status_code=429, detail="Too many requests. Slow down.")
            window.append(now)
        return await call_next(request)


def safe_detail(exc: Exception) -> str:
    """Return a user-safe message, never a raw stack trace / internal path (A09)."""
    # Known, already-safe messages pass through; everything else is generic.
    msg = str(exc)
    if len(msg) > 200 or "\n" in msg or "Traceback" in msg:
        return "Could not process the request."
    return msg
