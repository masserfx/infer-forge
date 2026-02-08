"""Tests for orchestration pipeline router."""


from app.orchestration.router import route_classification


class TestRouteClassification:
    def test_poptavka_with_attachments(self):
        stages = route_classification("poptavka", 0.9, has_attachments=True)
        assert "process_attachments" in stages
        assert "parse_email" in stages
        assert "orchestrate_order" in stages
        assert "auto_calculate" in stages

    def test_poptavka_without_attachments(self):
        stages = route_classification("poptavka", 0.9, has_attachments=False)
        assert "process_attachments" not in stages
        assert "parse_email" in stages
        assert "auto_calculate" in stages

    def test_objednavka_routes(self):
        stages = route_classification("objednavka", 0.85, has_attachments=False)
        assert "parse_email" in stages
        assert "orchestrate_order" in stages
        assert "auto_calculate" not in stages

    def test_faktura_routes(self):
        stages = route_classification("faktura", 0.90, has_attachments=True)
        assert "process_attachments" in stages
        assert "parse_email" in stages
        assert "orchestrate_order" in stages

    def test_reklamace_escalates(self):
        stages = route_classification("reklamace", 0.88, has_attachments=False)
        assert "parse_email" in stages
        assert "escalate" in stages
        assert "auto_calculate" not in stages

    def test_obchodni_sdeleni_archives(self):
        stages = route_classification("obchodni_sdeleni", 0.95, has_attachments=False)
        assert "archive" in stages

    def test_dotaz_routes(self):
        stages = route_classification("dotaz", 0.80, has_attachments=False)
        assert "orchestrate_order" in stages
        assert "notify" in stages

    def test_priloha_with_attachments(self):
        stages = route_classification("priloha", 0.85, has_attachments=True)
        assert "process_attachments" in stages

    def test_priloha_without_attachments_reviews(self):
        stages = route_classification("priloha", 0.85, has_attachments=False)
        assert "review" in stages

    def test_low_confidence_triggers_review(self):
        stages = route_classification("poptavka", 0.5, has_attachments=False)
        assert stages == ["review"]

    def test_needs_review_flag(self):
        stages = route_classification("poptavka", 0.9, has_attachments=False, needs_review=True)
        assert stages == ["review"]

    def test_informace_zakazka_routes(self):
        stages = route_classification("informace_zakazka", 0.85, has_attachments=False)
        assert "parse_email" in stages
        assert "orchestrate_order" in stages
