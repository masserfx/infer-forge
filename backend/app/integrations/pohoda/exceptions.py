"""Custom exceptions for Pohoda integration.

All Pohoda-related errors inherit from PohodaError base class
for easier exception handling.
"""


class PohodaError(Exception):
    """Base exception for Pohoda integration."""


class PohodaConnectionError(PohodaError):
    """Connection to mServer failed.

    Raised when HTTP client cannot establish connection to Pohoda mServer,
    typically due to network issues, DNS resolution, or server unavailability.
    """


class PohodaResponseError(PohodaError):
    """mServer returned error response.

    Raised when mServer responds with HTTP error status code (4xx, 5xx)
    or returns valid XML but with error states.
    """

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize response error with optional HTTP status code.

        Args:
            message: Error description
            status_code: HTTP status code if available
        """
        self.status_code = status_code
        super().__init__(message)


class PohodaXMLError(PohodaError):
    """XML parsing or validation error.

    Raised when XML document cannot be parsed, is malformed,
    or doesn't conform to expected Pohoda schema.
    """
