"""Tests for orchestration data models."""


from app.models.email_attachment import OCRStatus
from app.models.inbox import InboxClassification, InboxStatus
from app.models.processing_task import ProcessingStage, ProcessingStatus


class TestOCRStatusEnum:
    def test_values(self):
        assert OCRStatus.PENDING.value == "pending"
        assert OCRStatus.RUNNING.value == "running"
        assert OCRStatus.COMPLETE.value == "complete"
        assert OCRStatus.FAILED.value == "failed"
        assert OCRStatus.SKIPPED.value == "skipped"


class TestProcessingStageEnum:
    def test_all_stages(self):
        stages = [s.value for s in ProcessingStage]
        assert "ingest" in stages
        assert "classify" in stages
        assert "parse" in stages
        assert "ocr" in stages
        assert "analyze" in stages
        assert "orchestrate" in stages
        assert "calculate" in stages
        assert "offer" in stages
        assert len(stages) == 8


class TestProcessingStatusEnum:
    def test_all_statuses(self):
        statuses = [s.value for s in ProcessingStatus]
        assert "pending" in statuses
        assert "running" in statuses
        assert "success" in statuses
        assert "failed" in statuses
        assert "dlq" in statuses


class TestInboxClassificationExtended:
    def test_new_categories(self):
        assert InboxClassification.INFORMACE_ZAKAZKA.value == "informace_zakazka"
        assert InboxClassification.FAKTURA.value == "faktura"
        assert InboxClassification.OBCHODNI_SDELENI.value == "obchodni_sdeleni"

    def test_existing_categories_preserved(self):
        assert InboxClassification.POPTAVKA.value == "poptavka"
        assert InboxClassification.OBJEDNAVKA.value == "objednavka"
        assert InboxClassification.REKLAMACE.value == "reklamace"
        assert InboxClassification.DOTAZ.value == "dotaz"
        assert InboxClassification.PRILOHA.value == "priloha"


class TestInboxStatusExtended:
    def test_new_statuses(self):
        assert InboxStatus.CLASSIFIED.value == "classified"
        assert InboxStatus.REVIEW.value == "review"
        assert InboxStatus.ARCHIVED.value == "archived"

    def test_existing_statuses_preserved(self):
        assert InboxStatus.NEW.value == "new"
        assert InboxStatus.PROCESSING.value == "processing"
        assert InboxStatus.PROCESSED.value == "processed"
        assert InboxStatus.ESCALATED.value == "escalated"
