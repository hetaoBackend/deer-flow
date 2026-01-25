"""Custom exceptions for sandbox providers."""


class K8sSandboxError(Exception):
    """Base exception for Kubernetes sandbox operations.

    This exception provides detailed error information for K8s-specific
    failures, allowing upper layers to distinguish K8s errors from
    general sandbox errors.
    """

    def __init__(self, message: str, reason: str | None = None, status_code: int | None = None):
        """Initialize K8s sandbox error.

        Args:
            message: Human-readable error message.
            reason: K8s API error reason (e.g., 'NotFound', 'Forbidden').
            status_code: HTTP status code from K8s API response.
        """
        super().__init__(message)
        self.reason = reason
        self.status_code = status_code

    def __str__(self) -> str:
        """Return formatted error message."""
        parts = [super().__str__()]
        if self.reason:
            parts.append(f"Reason: {self.reason}")
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        return " | ".join(parts)
