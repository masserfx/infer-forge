"""Tests for email auto-reply functionality."""

from unittest.mock import MagicMock, patch

import pytest

from app.integrations.email.tasks import (
    _generate_auto_reply_body,
    send_auto_reply,
)


class TestAutoReplyBodyGeneration:
    """Test auto-reply body text generation."""

    def test_poptavka_classification(self):
        """Test body for inquiry classification."""
        body = _generate_auto_reply_body(classification="poptavka", order_number=None)
        assert "poptávku" in body
        assert "cenovou nabídku" in body
        assert "2 pracovních dnů" in body

    def test_objednavka_classification(self):
        """Test body for order classification."""
        body = _generate_auto_reply_body(classification="objednavka", order_number=None)
        assert "objednávku" in body
        assert "přípravou zakázky" in body
        assert "Potvrzení objednávky" in body

    def test_reklamace_classification(self):
        """Test body for complaint classification."""
        body = _generate_auto_reply_body(classification="reklamace", order_number=None)
        assert "reklamace" in body
        assert "mrzí" in body
        assert "24 hodin" in body

    def test_with_order_number(self):
        """Test body when order number is provided."""
        body = _generate_auto_reply_body(classification="dotaz", order_number="ZAK-2024-001")
        assert "ZAK-2024-001" in body
        assert "zakázky" in body

    def test_unknown_classification(self):
        """Test body for unknown/other classification."""
        body = _generate_auto_reply_body(classification="dotaz", order_number=None)
        assert "Děkujeme za Váš email" in body
        assert "přijali" in body


class TestSendAutoReply:
    """Test send_auto_reply function."""

    @patch("app.integrations.email.tasks.get_settings")
    def test_blocked_when_sending_disabled(self, mock_settings):
        """Test that sending is blocked when EMAIL_SENDING_ENABLED=false."""
        mock_settings.return_value.EMAIL_SENDING_ENABLED = False
        mock_settings.return_value.SMTP_HOST = "smtp.example.com"

        result = send_auto_reply(
            to_email="customer@example.com",
            subject="Re: Test",
        )

        assert result["status"] == "blocked"
        assert "EMAIL_SENDING_ENABLED" in result["reason"]

    @patch("app.integrations.email.tasks.get_settings")
    def test_skipped_when_smtp_not_configured(self, mock_settings):
        """Test that sending is skipped when SMTP_HOST is not configured."""
        mock_settings.return_value.EMAIL_SENDING_ENABLED = True
        mock_settings.return_value.SMTP_HOST = ""

        result = send_auto_reply(
            to_email="customer@example.com",
            subject="Re: Test",
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "SMTP not configured"

    @patch("app.integrations.email.tasks.smtplib.SMTP_SSL")
    @patch("app.integrations.email.tasks.get_settings")
    @patch("app.integrations.email.tasks.Environment")
    def test_sends_email_successfully(self, mock_env, mock_settings, mock_smtp):
        """Test successful email sending."""
        # Mock settings
        settings = MagicMock()
        settings.EMAIL_SENDING_ENABLED = True
        settings.SMTP_HOST = "smtp.example.com"
        settings.SMTP_PORT = 465
        settings.SMTP_USER = "test@example.com"
        settings.SMTP_PASSWORD = "password123"
        settings.SMTP_FROM_EMAIL = "test@example.com"
        settings.SMTP_USE_TLS = True
        settings.POHODA_ICO = "04856562"
        mock_settings.return_value = settings

        # Mock Jinja2 template
        mock_template = MagicMock()
        mock_template.render.return_value = "<html><body>Test email</body></html>"
        mock_env.return_value.get_template.return_value = mock_template

        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = send_auto_reply(
            to_email="customer@example.com",
            subject="Re: Test inquiry",
            order_number="ZAK-2024-001",
            classification="poptavka",
            original_message_id="<original@example.com>",
        )

        # Assertions
        assert result["status"] == "sent"
        assert result["to_email"] == "customer@example.com"
        assert "timestamp" in result

        # Verify SMTP methods were called
        mock_server.login.assert_called_once_with("test@example.com", "password123")
        mock_server.send_message.assert_called_once()

    @patch("app.integrations.email.tasks.smtplib.SMTP")
    @patch("app.integrations.email.tasks.get_settings")
    @patch("app.integrations.email.tasks.Environment")
    def test_uses_starttls_for_port_587(self, mock_env, mock_settings, mock_smtp):
        """Test that STARTTLS is used for port 587."""
        # Mock settings with port 587
        settings = MagicMock()
        settings.EMAIL_SENDING_ENABLED = True
        settings.SMTP_HOST = "smtp.example.com"
        settings.SMTP_PORT = 587
        settings.SMTP_USER = "test@example.com"
        settings.SMTP_PASSWORD = "password123"
        settings.SMTP_FROM_EMAIL = "test@example.com"
        settings.SMTP_USE_TLS = True
        settings.POHODA_ICO = "04856562"
        mock_settings.return_value = settings

        # Mock template
        mock_template = MagicMock()
        mock_template.render.return_value = "<html><body>Test</body></html>"
        mock_env.return_value.get_template.return_value = mock_template

        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_auto_reply(
            to_email="customer@example.com",
            subject="Re: Test",
        )

        # Verify STARTTLS was called
        mock_server.starttls.assert_called_once()

    @patch("app.integrations.email.tasks.get_settings")
    @patch("app.integrations.email.tasks.Environment")
    def test_handles_smtp_error(self, mock_env, mock_settings):
        """Test error handling when SMTP fails."""
        # Mock settings
        settings = MagicMock()
        settings.EMAIL_SENDING_ENABLED = True
        settings.SMTP_HOST = "smtp.example.com"
        settings.SMTP_PORT = 465
        settings.SMTP_FROM_EMAIL = "test@example.com"
        settings.POHODA_ICO = "04856562"
        mock_settings.return_value = settings

        # Mock template
        mock_template = MagicMock()
        mock_template.render.return_value = "<html><body>Test</body></html>"
        mock_env.return_value.get_template.return_value = mock_template

        # Mock SMTP to raise exception
        with patch("app.integrations.email.tasks.smtplib.SMTP_SSL") as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP connection failed")

            with pytest.raises(Exception, match="SMTP connection failed"):
                send_auto_reply(
                    to_email="customer@example.com",
                    subject="Re: Test",
                )


class TestSendAutoReplyTask:
    """Test Celery task wrapper for auto-reply."""

    @patch("app.integrations.email.tasks.smtplib.SMTP_SSL")
    @patch("app.integrations.email.tasks.get_settings")
    @patch("app.integrations.email.tasks.Environment")
    def test_task_success(self, mock_env, mock_settings, mock_smtp):
        """Test successful task execution."""
        # Mock settings
        settings = MagicMock()
        settings.EMAIL_SENDING_ENABLED = True
        settings.SMTP_HOST = "smtp.example.com"
        settings.SMTP_PORT = 465
        settings.SMTP_FROM_EMAIL = "test@example.com"
        settings.POHODA_ICO = "04856562"
        mock_settings.return_value = settings

        # Mock template
        mock_template = MagicMock()
        mock_template.render.return_value = "<html><body>Test</body></html>"
        mock_env.return_value.get_template.return_value = mock_template

        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = send_auto_reply(
            to_email="customer@example.com",
            subject="Re: Test",
        )

        assert result["status"] == "sent"

    @patch("app.integrations.email.tasks.smtplib.SMTP_SSL")
    @patch("app.integrations.email.tasks.get_settings")
    @patch("app.integrations.email.tasks.Environment")
    def test_task_includes_threading_headers(self, mock_env, mock_settings, mock_smtp):
        """Test that task passes original message ID for email threading."""
        # Mock settings
        settings = MagicMock()
        settings.EMAIL_SENDING_ENABLED = True
        settings.SMTP_HOST = "smtp.example.com"
        settings.SMTP_PORT = 465
        settings.SMTP_FROM_EMAIL = "test@example.com"
        settings.POHODA_ICO = "04856562"
        mock_settings.return_value = settings

        # Mock template
        mock_template = MagicMock()
        mock_template.render.return_value = "<html><body>Test</body></html>"
        mock_env.return_value.get_template.return_value = mock_template

        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = send_auto_reply(
            to_email="customer@example.com",
            subject="Re: Test",
            original_message_id="<original@example.com>",
        )

        # Verify email was sent
        assert result["status"] == "sent"
        mock_server.send_message.assert_called_once()

        # Verify message had threading headers
        msg_arg = mock_server.send_message.call_args[0][0]
        assert msg_arg["In-Reply-To"] == "<original@example.com>"
        assert msg_arg["References"] == "<original@example.com>"
