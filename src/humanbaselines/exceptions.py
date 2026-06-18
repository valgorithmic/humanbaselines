"""Typed exception hierarchy for the Human Crash Baselines client.

Every non-2xx response is mapped to one of these by status code, so callers can
catch the specific failure they care about (auth vs. validation vs. warm-up)
rather than parsing HTTP codes themselves.
"""

from __future__ import annotations

from typing import Any


class HumanBaselinesError(Exception):
    """Base class for all client errors."""


class APIError(HumanBaselinesError):
    """A non-2xx HTTP response that isn't covered by a more specific subclass.

    Carries the HTTP `status_code` and the parsed/raw response `body`.
    """

    def __init__(self, message: str, *, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class AuthenticationError(APIError):
    """401 — missing or invalid API key."""


class ValidationError(APIError):
    """422 — the request failed server-side validation.

    `errors` holds the server's field-level detail (FastAPI's `detail` list)
    when present, so callers can see exactly which filter was rejected.
    """

    def __init__(self, message: str, *, status_code: int | None = None, body: Any = None):
        super().__init__(message, status_code=status_code, body=body)
        self.errors = body.get("detail") if isinstance(body, dict) else None


class NotFoundError(APIError):
    """404 — unknown route, or a county/resource that isn't loaded."""


class ServiceUnavailableError(APIError):
    """503 — the service is warming up (caches loading) or temporarily down.

    The client retries these automatically before giving up; if you see this,
    the retries were exhausted.
    """
