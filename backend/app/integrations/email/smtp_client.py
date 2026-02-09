"""Async SMTP client for sending emails.

Uses aiosmtplib for async email sending.
SSL connection on port 465.
"""

import mimetypes
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
import structlog

logger = structlog.get_logger(__name__)


class SMTPClient:
    """Async SMTP client for sending emails.

    Uses aiosmtplib for async operation.
    Supports SSL connection (port 465), attachments, error handling.
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout: int = 30,
    ) -> None:
        """Initialize SMTP client.

        Args:
            host: SMTP server hostname.
            port: SMTP server port (usually 465 for SSL, 587 for STARTTLS).
            user: Email username (used as sender address).
            password: Email password.
            timeout: Connection timeout in seconds.
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.timeout = timeout

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        attachments: list[str | Path] | None = None,
        html: bool = False,
        message_id: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
    ) -> bool:
        """Send email with optional attachments.

        Args:
            to: Recipient email address or list of addresses.
            subject: Email subject.
            body: Email body text (plain text or HTML).
            attachments: Optional list of file paths to attach.
            html: If True, treat body as HTML content.
            message_id: Optional Message-ID header for the outgoing email.
            in_reply_to: Optional In-Reply-To header for threading.
            references: Optional References header for threading.

        Returns:
            True if email sent successfully, False otherwise.

        Raises:
            aiosmtplib.SMTPException: If SMTP operation fails.
            FileNotFoundError: If attachment file not found.
        """
        # Safety switch — block all sending unless explicitly enabled
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.EMAIL_SENDING_ENABLED:
            recipients = [to] if isinstance(to, str) else to
            logger.warning(
                "smtp_send_blocked",
                reason="EMAIL_SENDING_ENABLED=false",
                recipients=recipients,
                subject=subject,
            )
            return False

        # Normalize recipient list
        recipients = [to] if isinstance(to, str) else to

        logger.info(
            "smtp_send_start",
            recipients=recipients,
            subject=subject,
            attachment_count=len(attachments) if attachments else 0,
        )

        try:
            # Create message
            message = self._create_message(
                to=recipients,
                subject=subject,
                body=body,
                attachments=attachments,
                html=html,
                message_id=message_id,
                in_reply_to=in_reply_to,
                references=references,
            )

            # Send email
            await self._send_message(message, recipients)

            logger.info(
                "smtp_send_success",
                recipients=recipients,
                subject=subject,
            )
            return True

        except aiosmtplib.SMTPException as e:
            logger.error(
                "smtp_send_failed",
                error=str(e),
                recipients=recipients,
                subject=subject,
            )
            raise
        except FileNotFoundError as e:
            logger.error(
                "smtp_attachment_not_found",
                error=str(e),
                recipients=recipients,
            )
            raise
        except Exception as e:
            logger.error(
                "smtp_send_unexpected_error",
                error=str(e),
                recipients=recipients,
            )
            return False

    def _create_message(
        self,
        to: list[str],
        subject: str,
        body: str,
        attachments: list[str | Path] | None,
        html: bool,
        message_id: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
    ) -> MIMEMultipart:
        """Create MIME message with body and attachments.

        Args:
            to: List of recipient addresses.
            subject: Email subject.
            body: Email body text.
            attachments: Optional list of file paths.
            html: If True, use HTML content type.
            message_id: Optional Message-ID header.
            in_reply_to: Optional In-Reply-To header for threading.
            references: Optional References header for threading.

        Returns:
            Constructed MIMEMultipart message.
        """
        message = MIMEMultipart()
        message["From"] = self.user
        message["To"] = ", ".join(to)
        message["Subject"] = subject

        # Threading headers
        if message_id:
            message["Message-ID"] = message_id
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
        if references:
            message["References"] = references

        # Attach body
        content_type = "html" if html else "plain"
        message.attach(MIMEText(body, content_type, "utf-8"))

        # Attach files
        if attachments:
            for attachment_path in attachments:
                self._attach_file(message, Path(attachment_path))

        return message

    def _attach_file(self, message: MIMEMultipart, file_path: Path) -> None:
        """Attach file to MIME message.

        Args:
            message: MIMEMultipart message to attach to.
            file_path: Path to file to attach.

        Raises:
            FileNotFoundError: If file does not exist.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        # Read file content
        with open(file_path, "rb") as f:
            file_data = f.read()

        # Guess MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        # Create attachment
        attachment = MIMEApplication(file_data, _subtype=mime_type.split("/")[1])
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=file_path.name,
        )

        message.attach(attachment)

        logger.debug(
            "smtp_attachment_added",
            filename=file_path.name,
            mime_type=mime_type,
            size=len(file_data),
        )

    async def _send_message(self, message: MIMEMultipart, recipients: list[str]) -> None:
        """Send MIME message via SMTP.

        Args:
            message: MIMEMultipart message to send.
            recipients: List of recipient addresses.

        Raises:
            aiosmtplib.SMTPException: If SMTP operation fails.
        """
        logger.debug("smtp_connect_start", host=self.host, port=self.port)

        # Determine use_tls based on port
        use_tls = self.port == 465

        async with aiosmtplib.SMTP(
            hostname=self.host,
            port=self.port,
            timeout=self.timeout,
            use_tls=use_tls,  # SSL for port 465
        ) as smtp:
            # Authenticate
            await smtp.login(self.user, self.password)
            logger.debug("smtp_auth_success", user=self.user)

            # Send message
            await smtp.send_message(message)
            logger.debug("smtp_message_sent", recipients=recipients)

    async def test_connection(self) -> bool:
        """Test SMTP connection and authentication.

        Returns:
            True if connection successful, False otherwise.
        """
        logger.info("smtp_test_connection_start", host=self.host, port=self.port)

        try:
            use_tls = self.port == 465

            async with aiosmtplib.SMTP(
                hostname=self.host,
                port=self.port,
                timeout=self.timeout,
                use_tls=use_tls,
            ) as smtp:
                await smtp.login(self.user, self.password)

            logger.info("smtp_test_connection_success", host=self.host)
            return True

        except aiosmtplib.SMTPException as e:
            logger.error("smtp_test_connection_failed", error=str(e), host=self.host)
            return False
        except Exception as e:
            logger.error("smtp_test_connection_unexpected_error", error=str(e))
            return False
