"""Exceptions for the Bijou v2 Python SDK."""

from typing import Any


class BijouApiError(Exception):
    """Base exception for errors returned by or communicating with the Bijou API."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        detail: Any = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail
        self.response_body = response_body


class BijouNotFoundError(BijouApiError):
    """Raised when an entity or resource is not found (HTTP 404)."""


class BijouValidationError(BijouApiError):
    """Raised when a payload fails schema validation or DAG acyclicity rules (HTTP 400 / 422)."""


class BijouPermissionDeniedError(BijouApiError):
    """Raised when an action violates organizational perspective permissions (HTTP 403)."""


class BijouPayloadTooLargeError(BijouApiError):
    """Raised when the request payload exceeds server limits (HTTP 413)."""


class BijouServiceUnavailableError(BijouApiError):
    """Raised when an upstream reasoning or engine dependency is offline (HTTP 503)."""


class BijouConnectionError(BijouApiError):
    """Raised when failing to establish HTTP/network transport to the Bijou server."""
