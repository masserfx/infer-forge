"""Async HTTP client for Pohoda mServer API.

This module provides HTTP communication layer for sending XML documents
to Pohoda mServer and receiving responses.
"""

import asyncio
import logging
from typing import Any

import httpx

from .exceptions import PohodaConnectionError, PohodaResponseError

logger = logging.getLogger(__name__)


class PohodaClient:
    """Async HTTP client for Pohoda mServer API.

    Handles HTTP communication with Pohoda mServer including:
    - Sending XML documents (Windows-1250 encoded)
    - Receiving and returning XML responses
    - Retry logic with exponential backoff
    - Proper error handling and logging

    Example:
        async with PohodaClient(base_url, ico) as client:
            response = await client.send_xml(xml_bytes)
    """

    def __init__(
        self,
        base_url: str,
        ico: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize Pohoda HTTP client.

        Args:
            base_url: mServer base URL (e.g. "http://localhost:8080")
            ico: Company IČO for identification
            timeout: Request timeout in seconds (default 30s)
            max_retries: Maximum number of retry attempts for connection errors
        """
        self.base_url = base_url.rstrip("/")
        self.ico = ico
        self.timeout = timeout
        self.max_retries = max_retries

        self._client: httpx.AsyncClient | None = None
        logger.info(
            "Initialized PohodaClient for IČO %s, mServer: %s",
            ico,
            base_url,
        )

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client instance.

        Returns:
            Configured AsyncClient instance
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    async def send_xml(self, xml_data: bytes) -> bytes:
        """Send XML to mServer and return response bytes.

        Implements retry logic with exponential backoff for connection errors.
        HTTP errors (4xx, 5xx) are not retried as they indicate server-side issues.

        Args:
            xml_data: XML document as bytes (Windows-1250 encoded)

        Returns:
            Response XML bytes from mServer

        Raises:
            PohodaConnectionError: If connection to mServer fails after retries
            PohodaResponseError: If mServer returns error HTTP status
        """
        client = self._get_client()
        endpoint = f"{self.base_url}/xml"

        headers = {
            "Content-Type": "application/xml; charset=Windows-1250",
        }

        logger.debug(
            "Sending XML to mServer: %s (size: %d bytes)",
            endpoint,
            len(xml_data),
        )

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await client.post(
                    endpoint,
                    content=xml_data,
                    headers=headers,
                )

                # Check HTTP status
                if response.status_code != 200:
                    error_msg = (
                        f"mServer returned HTTP {response.status_code}: " f"{response.text[:200]}"
                    )
                    logger.error(error_msg)
                    raise PohodaResponseError(
                        error_msg,
                        status_code=response.status_code,
                    )

                logger.info(
                    "Successfully received response from mServer " "(size: %d bytes)",
                    len(response.content),
                )
                return response.content

            except httpx.ConnectError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2**attempt
                    logger.warning(
                        "Connection failed (attempt %d/%d), " "retrying in %ds: %s",
                        attempt + 1,
                        self.max_retries,
                        wait_time,
                        str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Connection failed after %d attempts: %s",
                        self.max_retries,
                        str(e),
                    )

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "Request timeout (attempt %d/%d), " "retrying in %ds",
                        attempt + 1,
                        self.max_retries,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Request timeout after %d attempts",
                        self.max_retries,
                    )

            except PohodaResponseError:
                # Don't retry on HTTP errors (4xx, 5xx)
                raise

            except Exception as e:
                # Unexpected errors - don't retry
                logger.exception("Unexpected error sending XML to mServer")
                raise PohodaConnectionError(
                    f"Unexpected error: {type(e).__name__}: {str(e)}"
                ) from e

        # All retries exhausted
        raise PohodaConnectionError(
            f"Failed to connect to mServer after {self.max_retries} attempts: " f"{str(last_error)}"
        ) from last_error

    async def close(self) -> None:
        """Close underlying HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("PohodaClient closed")

    async def __aenter__(self) -> "PohodaClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit - ensures client is closed."""
        await self.close()
