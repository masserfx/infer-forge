"""Tests for EmailIngestionAgent."""


from app.orchestration.agents.email_ingestion import EmailIngestionAgent


class TestEmailIngestionAgent:
    def setup_method(self):
        self.agent = EmailIngestionAgent()

    def test_extract_thread_id_from_references(self):
        thread_id = self.agent._extract_thread_id(
            references_header="<abc123@mail.com> <def456@mail.com>",
            in_reply_to_header=None,
        )
        assert thread_id == "abc123@mail.com"

    def test_extract_thread_id_from_in_reply_to(self):
        thread_id = self.agent._extract_thread_id(
            references_header=None,
            in_reply_to_header="<reply123@mail.com>",
        )
        assert thread_id == "reply123@mail.com"

    def test_extract_thread_id_references_priority(self):
        thread_id = self.agent._extract_thread_id(
            references_header="<ref001@mail.com>",
            in_reply_to_header="<reply001@mail.com>",
        )
        assert thread_id == "ref001@mail.com"

    def test_extract_thread_id_none(self):
        thread_id = self.agent._extract_thread_id(None, None)
        assert thread_id is None

    def test_sanitize_filename_path_separators(self):
        result = self.agent._sanitize_filename("path/to/file.pdf")
        assert "/" not in result
        assert result == "path_to_file.pdf"

    def test_sanitize_filename_backslash(self):
        result = self.agent._sanitize_filename("C:\\Users\\file.pdf")
        assert "\\" not in result

    def test_sanitize_filename_null_bytes(self):
        result = self.agent._sanitize_filename("file\x00name.pdf")
        assert "\x00" not in result

    def test_sanitize_filename_long_name(self):
        long_name = "a" * 300 + ".pdf"
        result = self.agent._sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".pdf")
