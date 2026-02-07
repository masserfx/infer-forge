"""Unit tests for email polling and cleanup Celery tasks."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.email_classifier import ClassificationResult
from app.integrations.email.imap_client import RawEmail
from app.integrations.email.tasks import (
    _cleanup_processed_emails_async,
    _poll_inbox_async,
)
from app.models.inbox import InboxClassification, InboxMessage, InboxStatus


class TestPollInbox:
    """Tests for poll_inbox Celery task wrapper.

    Note: These tests focus on the async implementation (_poll_inbox_async).
    The Celery wrapper is minimal and harder to test without a real Celery context.
    """

    pass  # Skipping Celery wrapper tests - testing async implementation instead


class TestPollInboxAsync:
    """Tests for async implementation of inbox polling."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.IMAP_HOST = "imap.example.com"
        settings.IMAP_PORT = 993
        settings.IMAP_USER = "test@example.com"
        settings.IMAP_PASSWORD = "password123"
        settings.ANTHROPIC_API_KEY = "test-api-key"
        return settings

    @pytest.fixture
    def sample_raw_emails(self) -> list[RawEmail]:
        """Create sample raw emails."""
        return [
            RawEmail(
                message_id="msg-001@example.com",
                from_email="customer@example.com",
                subject="Poptávka na díly",
                body_text="Dobrý den, prosím o cenovou nabídku...",
                received_at=datetime.utcnow(),
                attachments=[],
            ),
            RawEmail(
                message_id="msg-002@example.com",
                from_email="support@example.com",
                subject="Dotaz na zakázku",
                body_text="Jaký je stav zakázky #123?",
                received_at=datetime.utcnow(),
                attachments=[],
            ),
        ]

    @pytest.mark.asyncio
    @patch("app.integrations.email.tasks.AsyncSessionLocal")
    @patch("app.integrations.email.tasks.EmailClassifier")
    @patch("app.integrations.email.tasks.IMAPClient")
    async def test_poll_inbox_async_processes_emails(
        self,
        mock_imap_client_class: MagicMock,
        mock_classifier_class: MagicMock,
        mock_session_local: MagicMock,
        mock_settings: MagicMock,
        sample_raw_emails: list[RawEmail],
    ) -> None:
        """Test async polling processes emails and creates inbox records."""
        # Mock IMAP client
        mock_imap = AsyncMock()
        mock_imap.connect = AsyncMock()
        mock_imap.fetch_new_messages = AsyncMock(return_value=sample_raw_emails)
        mock_imap.disconnect = AsyncMock()
        mock_imap_client_class.return_value = mock_imap

        # Mock email classifier
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(
            return_value=ClassificationResult(
                category="poptavka",
                confidence=0.95,
                reasoning="Email contains inquiry",
                needs_escalation=False,
            )
        )
        mock_classifier_class.return_value = mock_classifier

        # Track session usage
        checked_emails = []
        added_emails = []

        def create_check_session() -> AsyncMock:
            """Create session that returns None for scalar_one_or_none (no existing message)."""
            mock_session = AsyncMock()
            mock_result = MagicMock()  # Not AsyncMock - scalar_one_or_none is sync in sqlalchemy

            async def execute_check(stmt: object) -> MagicMock:
                # Track which email was checked
                checked_emails.append("checked")
                return mock_result

            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_session.execute = execute_check

            mock_session_context = AsyncMock()
            mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_context.__aexit__ = AsyncMock(return_value=None)
            return mock_session_context

        def create_insert_session() -> AsyncMock:
            """Create session for inserting message."""
            mock_session = AsyncMock()

            def add_message(msg: InboxMessage) -> None:
                added_emails.append(msg.message_id)

            mock_session.add = add_message
            mock_session.commit = AsyncMock()

            mock_session_context = AsyncMock()
            mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_context.__aexit__ = AsyncMock(return_value=None)
            return mock_session_context

        # Alternate between check and insert sessions
        session_calls = []
        for _ in range(len(sample_raw_emails)):
            session_calls.append(create_check_session())
            session_calls.append(create_insert_session())

        mock_session_local.side_effect = session_calls

        result = await _poll_inbox_async(mock_settings)

        assert result["status"] == "completed"
        assert result["processed"] == 2
        assert result["skipped"] == 0
        assert result["errors"] == 0
        assert "timestamp" in result

        # Verify IMAP operations
        mock_imap.connect.assert_awaited_once()
        mock_imap.fetch_new_messages.assert_awaited_once_with(mailbox="INBOX")
        mock_imap.disconnect.assert_awaited_once()

        # Verify classification was called for each email
        assert mock_classifier.classify.await_count == 2

        # Verify emails were checked and added
        assert len(checked_emails) == 2
        assert len(added_emails) == 2

    @pytest.mark.asyncio
    @patch("app.integrations.email.tasks.AsyncSessionLocal")
    @patch("app.integrations.email.tasks.EmailClassifier")
    @patch("app.integrations.email.tasks.IMAPClient")
    async def test_poll_inbox_async_skips_duplicates(
        self,
        mock_imap_client_class: MagicMock,
        mock_classifier_class: MagicMock,
        mock_session_local: MagicMock,
        mock_settings: MagicMock,
        sample_raw_emails: list[RawEmail],
    ) -> None:
        """Test async polling skips duplicate message_ids."""
        mock_imap = AsyncMock()
        mock_imap.connect = AsyncMock()
        mock_imap.fetch_new_messages = AsyncMock(return_value=[sample_raw_emails[0]])
        mock_imap.disconnect = AsyncMock()
        mock_imap_client_class.return_value = mock_imap

        mock_classifier = AsyncMock()
        mock_classifier_class.return_value = mock_classifier

        # Mock database session - message already exists
        existing_message = InboxMessage(
            message_id="msg-001@example.com",
            from_email="customer@example.com",
            subject="Existing",
            body_text="Already processed",
            received_at=datetime.utcnow(),
            status=InboxStatus.PROCESSED,
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing_message)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_local.return_value = mock_session_context

        result = await _poll_inbox_async(mock_settings)

        assert result["status"] == "completed"
        assert result["processed"] == 0
        assert result["skipped"] == 1
        assert result["errors"] == 0

        # Classifier should not be called for duplicates
        mock_classifier.classify.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.integrations.email.tasks.AsyncSessionLocal")
    @patch("app.integrations.email.tasks.EmailClassifier")
    @patch("app.integrations.email.tasks.IMAPClient")
    async def test_poll_inbox_async_handles_classification_errors(
        self,
        mock_imap_client_class: MagicMock,
        mock_classifier_class: MagicMock,
        mock_session_local: MagicMock,
        mock_settings: MagicMock,
        sample_raw_emails: list[RawEmail],
    ) -> None:
        """Test async polling handles classification errors gracefully."""
        mock_imap = AsyncMock()
        mock_imap.connect = AsyncMock()
        mock_imap.fetch_new_messages = AsyncMock(return_value=[sample_raw_emails[0]])
        mock_imap.disconnect = AsyncMock()
        mock_imap_client_class.return_value = mock_imap

        # Mock classifier to raise exception
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(side_effect=Exception("API error"))
        mock_classifier_class.return_value = mock_classifier

        def create_check_session() -> AsyncMock:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_session.execute = AsyncMock(return_value=mock_result)

            mock_session_context = AsyncMock()
            mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_context.__aexit__ = AsyncMock(return_value=None)
            return mock_session_context

        mock_session_local.side_effect = [create_check_session()]

        result = await _poll_inbox_async(mock_settings)

        assert result["status"] == "completed"
        assert result["processed"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 1

        # IMAP should still disconnect even after error
        mock_imap.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.integrations.email.tasks.AsyncSessionLocal")
    @patch("app.integrations.email.tasks.EmailClassifier")
    @patch("app.integrations.email.tasks.IMAPClient")
    async def test_poll_inbox_async_sets_escalation_status(
        self,
        mock_imap_client_class: MagicMock,
        mock_classifier_class: MagicMock,
        mock_session_local: MagicMock,
        mock_settings: MagicMock,
        sample_raw_emails: list[RawEmail],
    ) -> None:
        """Test async polling sets ESCALATED status when needed."""
        mock_imap = AsyncMock()
        mock_imap.connect = AsyncMock()
        mock_imap.fetch_new_messages = AsyncMock(return_value=[sample_raw_emails[0]])
        mock_imap.disconnect = AsyncMock()
        mock_imap_client_class.return_value = mock_imap

        # Mock classifier with escalation flag
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(
            return_value=ClassificationResult(
                category="reklamace",
                confidence=0.85,
                reasoning="Urgent complaint",
                needs_escalation=True,
            )
        )
        mock_classifier_class.return_value = mock_classifier

        # Capture the inbox message that was added
        added_message = None

        def capture_add(msg: InboxMessage) -> None:
            nonlocal added_message
            added_message = msg

        def create_check_session() -> AsyncMock:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_session.execute = AsyncMock(return_value=mock_result)

            mock_session_context = AsyncMock()
            mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_context.__aexit__ = AsyncMock(return_value=None)
            return mock_session_context

        def create_insert_session() -> AsyncMock:
            mock_session = AsyncMock()
            mock_session.add = capture_add
            mock_session.commit = AsyncMock()

            mock_session_context = AsyncMock()
            mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_context.__aexit__ = AsyncMock(return_value=None)
            return mock_session_context

        mock_session_local.side_effect = [create_check_session(), create_insert_session()]

        result = await _poll_inbox_async(mock_settings)

        assert result["status"] == "completed"
        assert result["processed"] == 1

        # Verify escalated status was set
        assert added_message is not None
        assert added_message.status == InboxStatus.ESCALATED
        assert added_message.classification == InboxClassification.REKLAMACE


class TestCleanupProcessedEmails:
    """Tests for cleanup_processed_emails Celery task wrapper.

    Note: These tests focus on the async implementation (_cleanup_processed_emails_async).
    The Celery wrapper is minimal and harder to test without a real Celery context.
    """

    pass  # Skipping Celery wrapper tests - testing async implementation instead


class TestCleanupProcessedEmailsAsync:
    """Tests for async implementation of cleanup."""

    @pytest.mark.asyncio
    @patch("app.integrations.email.tasks.AsyncSessionLocal")
    async def test_cleanup_processed_emails_async_deletes_old_messages(
        self,
        mock_session_local: MagicMock,
    ) -> None:
        """Test async cleanup deletes messages older than 90 days."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.rowcount = 10
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_local.return_value = mock_session_context

        result = await _cleanup_processed_emails_async()

        assert result["status"] == "completed"
        assert result["deleted"] == 10
        assert "cutoff_date" in result
        assert "timestamp" in result

        # Verify database operations
        mock_session.execute.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.integrations.email.tasks.AsyncSessionLocal")
    async def test_cleanup_processed_emails_async_no_messages_to_delete(
        self,
        mock_session_local: MagicMock,
    ) -> None:
        """Test async cleanup when there are no old messages."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_local.return_value = mock_session_context

        result = await _cleanup_processed_emails_async()

        assert result["status"] == "completed"
        assert result["deleted"] == 0
