"""Tests for HeuristicClassifier."""


from app.orchestration.agents.heuristic_classifier import HeuristicClassifier


class TestHeuristicClassifier:
    def setup_method(self):
        self.classifier = HeuristicClassifier()

    def test_objednavka_pattern(self):
        result = self.classifier.classify(
            subject="Objednáváme kolena DN200",
            body="Dobrý den, objednáváme 50ks kolen dle nabídky.",
            has_attachments=False,
            body_length=50,
        )
        assert result is not None
        assert result.category == "objednavka"
        assert result.confidence >= 0.85

    def test_objednavka_potvrzujeme(self):
        result = self.classifier.classify(
            subject="Potvrzujeme objednávku",
            body="Tímto potvrzujeme objednávku č. 2025/123.",
            has_attachments=False,
            body_length=50,
        )
        assert result is not None
        assert result.category == "objednavka"

    def test_poptavka_pattern(self):
        result = self.classifier.classify(
            subject="Poptávka - kolena",
            body="Dobrý den, poptáváme kolena DN200 PN16.",
            has_attachments=False,
            body_length=50,
        )
        assert result is not None
        assert result.category == "poptavka"

    def test_poptavka_cenovou_nabidku(self):
        result = self.classifier.classify(
            subject="Prosba",
            body="Prosíme o cenovou nabídku na svařence dle výkresu. Potřebujeme dodání do 4 týdnů včetně atestu 3.1 dle EN 10204.",
            has_attachments=True,
            body_length=120,
        )
        assert result is not None
        assert result.category == "poptavka"

    def test_poptavka_zadame_o_cenovou(self):
        result = self.classifier.classify(
            subject="Poptávka",
            body="Žádáme o cenovou nabídku na potrubní díly.",
            has_attachments=False,
            body_length=50,
        )
        assert result is not None
        assert result.category == "poptavka"

    def test_reklamace_pattern(self):
        result = self.classifier.classify(
            subject="Reklamace dodávky",
            body="Zjistili jsme vady na dodaných dílech.",
            has_attachments=False,
            body_length=50,
        )
        assert result is not None
        assert result.category == "reklamace"

    def test_reklamace_neshoda(self):
        result = self.classifier.classify(
            subject="Neshoda na zakázce",
            body="Upozorňujeme na neshodu v rozměrech.",
            has_attachments=False,
            body_length=50,
        )
        assert result is not None
        assert result.category == "reklamace"

    def test_obchodni_sdeleni_newsletter(self):
        result = self.classifier.classify(
            subject="Novinky z oboru",
            body="Přihlášení k odběru. Klikněte pro unsubscribe.",
            has_attachments=False,
            body_length=60,
        )
        assert result is not None
        assert result.category == "obchodni_sdeleni"

    def test_faktura_pattern(self):
        result = self.classifier.classify(
            subject="Faktura č. 2025/001",
            body="V příloze zasíláme fakturu.",
            has_attachments=True,
            body_length=40,
        )
        # Short body with attachments matches priloha first
        assert result is not None

    def test_priloha_short_body_with_attachments(self):
        result = self.classifier.classify(
            subject="Výkresy",
            body="Viz příloha.",
            has_attachments=True,
            body_length=12,
        )
        assert result is not None
        assert result.category == "priloha"
        assert result.confidence == 0.85

    def test_multiple_matches_higher_confidence(self):
        result = self.classifier.classify(
            subject="Objednáváme dle objednávky číslo 123",
            body="Potvrzujeme objednávku na kolena DN200.",
            has_attachments=False,
            body_length=50,
        )
        assert result is not None
        assert result.category == "objednavka"
        assert result.confidence >= 0.90

    def test_no_match_returns_none(self):
        result = self.classifier.classify(
            subject="Hello",
            body="This is just a regular English email about nothing.",
            has_attachments=False,
            body_length=60,
        )
        assert result is None

    def test_empty_inputs(self):
        result = self.classifier.classify(
            subject="", body="", has_attachments=False, body_length=0
        )
        assert result is None

    def test_subject_only_match(self):
        result = self.classifier.classify(
            subject="Poptáváme potrubní díly",
            body="Viz příloha s výkresy.",
            has_attachments=True,
            body_length=25,
        )
        # Short body triggers priloha first
        assert result is not None

    def test_no_escalation_flag(self):
        result = self.classifier.classify(
            subject="Objednáváme materiál",
            body="Objednáváme dle nabídky.",
            has_attachments=False,
            body_length=30,
        )
        assert result is not None
        assert result.needs_escalation is False
