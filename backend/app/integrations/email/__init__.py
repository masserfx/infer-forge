"""Email integration module for INFER FORGE.

Provides async IMAP and SMTP clients for email operations.
"""

from app.integrations.email.imap_client import Attachment, IMAPClient, RawEmail
from app.integrations.email.smtp_client import SMTPClient

__all__ = [
    "Attachment",
    "IMAPClient",
    "RawEmail",
    "SMTPClient",
]
