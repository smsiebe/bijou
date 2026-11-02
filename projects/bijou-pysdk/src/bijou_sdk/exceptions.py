"""Client-side domain exceptions for bijou-pysdk."""

from typing import Any


class BijouApiError(Exception):
    """Base exception for all errors returned by or communicating with Bijou API."""

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
    """Raised when the payload fails schema or business validation (HTTP 422)."""


class BijouConnectionError(BijouApiError):
    """Raised when failing to establish transport or connect to the server."""
