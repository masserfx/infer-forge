"""Async IMAP client for fetching emails.

Uses synchronous imaplib in thread executor (aioimaplib is unstable).
Handles multipart messages, text/plain, text/html fallback.
SSL connection on port 993.
"""

import asyncio
import email
import imaplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header
from email.message import Message
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Attachment:
    """Email attachment data."""

    filename: str
    content_type: str
    data: bytes


@dataclass
class RawEmail:
    """Raw email message with metadata."""

    message_id: str
    from_email: str
    subject: str
    body_text: str
    received_at: datetime
    attachments: list[Attachment]


class IMAPClient:
    """Async IMAP client for fetching emails.

    Uses synchronous imaplib in thread executor for stability.
    Supports SSL connection (port 993), multipart parsing, error handling.
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout: int = 30,
    ) -> None:
        """Initialize IMAP client.

        Args:
            host: IMAP server hostname.
            port: IMAP server port (usually 993 for SSL).
            user: Email username.
            password: Email password.
            timeout: Connection timeout in seconds.
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.timeout = timeout
        self._connection: imaplib.IMAP4_SSL | None = None

    async def connect(self) -> None:
        """Establish SSL connection to IMAP server.

        Raises:
            imaplib.IMAP4.error: If connection or authentication fails.
            TimeoutError: If connection times out.
        """
        logger.info("imap_connect_start", host=self.host, port=self.port, user=self.user)

        try:
            # Run synchronous IMAP connection in thread executor
            loop = asyncio.get_running_loop()
            self._connection = await loop.run_in_executor(
                None,
                self._create_connection,
            )

            # Authenticate
            await loop.run_in_executor(
                None,
                self._connection.login,
                self.user,
                self.password,
            )

            logger.info("imap_connect_success", host=self.host, user=self.user)

        except imaplib.IMAP4.error as e:
            logger.error("imap_connect_auth_failed", error=str(e), user=self.user)
            raise
        except Exception as e:
            logger.error("imap_connect_failed", error=str(e), host=self.host)
            raise

    def _create_connection(self) -> imaplib.IMAP4_SSL:
        """Create synchronous SSL IMAP connection.

        Returns:
            imaplib.IMAP4_SSL: Connected IMAP client.
        """
        ssl_context = ssl.create_default_context()
        return imaplib.IMAP4_SSL(
            host=self.host,
            port=self.port,
            ssl_context=ssl_context,
            timeout=self.timeout,
        )

    async def disconnect(self) -> None:
        """Close IMAP connection gracefully."""
        if self._connection is None:
            return

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._connection.logout)
            logger.info("imap_disconnect_success", user=self.user)
        except Exception as e:
            logger.warning("imap_disconnect_error", error=str(e))
        finally:
            self._connection = None

    async def fetch_new_messages(self, mailbox: str = "INBOX") -> list[RawEmail]:
        """Fetch new (unseen) messages from mailbox.

        Args:
            mailbox: Mailbox name to fetch from (default: INBOX).

        Returns:
            List of RawEmail objects with parsed content and attachments.

        Raises:
            ValueError: If client is not connected.
            imaplib.IMAP4.error: If mailbox selection or fetch fails.
        """
        if self._connection is None:
            raise ValueError("IMAP client not connected. Call connect() first.")

        logger.info("imap_fetch_start", mailbox=mailbox, user=self.user)

        try:
            loop = asyncio.get_running_loop()

            # Select mailbox
            await loop.run_in_executor(
                None,
                self._connection.select,
                mailbox,
                True,  # readonly=True
            )

            # Search for unseen messages
            status, message_ids_data = await loop.run_in_executor(
                None,
                self._connection.search,
                None,
                "UNSEEN",
            )

            if status != "OK":
                logger.error("imap_search_failed", status=status)
                return []

            message_ids_str = message_ids_data[0].decode("utf-8")
            if not message_ids_str.strip():
                logger.info("imap_no_new_messages", mailbox=mailbox)
                return []

            message_ids = message_ids_str.split()
            logger.info("imap_found_messages", count=len(message_ids), mailbox=mailbox)

            # Fetch messages
            emails: list[RawEmail] = []
            for msg_id in message_ids:
                try:
                    raw_email = await self._fetch_single_message(msg_id.decode("utf-8"))
                    emails.append(raw_email)
                except Exception as e:
                    logger.error(
                        "imap_fetch_message_failed",
                        message_id=msg_id.decode("utf-8"),
                        error=str(e),
                    )
                    continue

            logger.info("imap_fetch_success", count=len(emails), mailbox=mailbox)
            return emails

        except imaplib.IMAP4.error as e:
            logger.error("imap_fetch_failed", error=str(e), mailbox=mailbox)
            raise
        except Exception as e:
            logger.error("imap_fetch_unexpected_error", error=str(e))
            raise

    async def _fetch_single_message(self, msg_id: str) -> RawEmail:
        """Fetch and parse single email message.

        Args:
            msg_id: IMAP message ID.

        Returns:
            Parsed RawEmail object.
        """
        if self._connection is None:
            raise ValueError("IMAP client not connected")

        loop = asyncio.get_running_loop()

        # Fetch message data
        status, msg_data = await loop.run_in_executor(
            None,
            self._connection.fetch,
            msg_id,
            "(RFC822)",
        )

        if status != "OK" or not msg_data or msg_data[0] is None:
            raise ValueError(f"Failed to fetch message {msg_id}")

        # Parse email message
        raw_email_bytes = msg_data[0][1]
        email_message = email.message_from_bytes(raw_email_bytes)

        return self._parse_email_message(email_message)

    def _parse_email_message(self, msg: Message) -> RawEmail:
        """Parse email.Message into RawEmail dataclass.

        Args:
            msg: Parsed email.Message object.

        Returns:
            RawEmail with extracted data.
        """
        # Extract headers
        message_id = msg.get("Message-ID", "")
        from_email = self._decode_header_value(msg.get("From", ""))
        subject = self._decode_header_value(msg.get("Subject", ""))

        # Parse date
        date_str = msg.get("Date", "")
        received_at = self._parse_date(date_str)

        # Extract body and attachments
        body_text = ""
        attachments: list[Attachment] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Extract text body (prefer text/plain, fallback to text/html)
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    body_text = self._get_text_from_part(part)
                    break  # Prefer text/plain

                if (
                    content_type == "text/html"
                    and not body_text
                    and "attachment" not in content_disposition
                ):
                    body_text = self._get_text_from_part(part)

                # Extract attachments
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header_value(filename)
                        payload = part.get_payload(decode=True)
                        if payload:
                            attachments.append(
                                Attachment(
                                    filename=filename,
                                    content_type=content_type,
                                    data=payload,
                                )
                            )
        else:
            # Single-part message
            content_type = msg.get_content_type()
            if content_type in ("text/plain", "text/html"):
                body_text = self._get_text_from_part(msg)

        return RawEmail(
            message_id=message_id,
            from_email=from_email,
            subject=subject,
            body_text=body_text.strip(),
            received_at=received_at,
            attachments=attachments,
        )

    def _get_text_from_part(self, part: Message) -> str:
        """Extract text from email part with charset decoding.

        Args:
            part: Email message part.

        Returns:
            Decoded text string.
        """
        payload = part.get_payload(decode=True)
        if not payload:
            return ""

        # Try to get charset
        charset = part.get_content_charset() or "utf-8"

        try:
            return payload.decode(charset, errors="replace")
        except (LookupError, AttributeError):
            # Fallback to utf-8
            return payload.decode("utf-8", errors="replace")

    def _decode_header_value(self, header_value: str) -> str:
        """Decode email header with RFC 2047 encoding.

        Args:
            header_value: Raw header value (may be encoded).

        Returns:
            Decoded string.
        """
        if not header_value:
            return ""

        decoded_parts = decode_header(header_value)
        result_parts: list[str] = []

        for part_bytes, charset in decoded_parts:
            if isinstance(part_bytes, bytes):
                # Decode bytes with charset
                charset = charset or "utf-8"
                try:
                    result_parts.append(part_bytes.decode(charset, errors="replace"))
                except (LookupError, AttributeError):
                    result_parts.append(part_bytes.decode("utf-8", errors="replace"))
            else:
                # Already a string
                result_parts.append(part_bytes)

        return "".join(result_parts)

    def _parse_date(self, date_str: str) -> datetime:
        """Parse email date string into datetime.

        Args:
            date_str: Email Date header value.

        Returns:
            Parsed datetime (UTC). Falls back to current time if parsing fails.
        """
        if not date_str:
            return datetime.utcnow()

        try:
            # Use email.utils.parsedate_to_datetime for RFC 2822 dates
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            logger.warning("imap_date_parse_failed", date_str=date_str)
            return datetime.utcnow()

    async def __aenter__(self) -> "IMAPClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
