"""Tests for DocumentTypeDetector."""


from app.orchestration.agents.document_type_detector import DocumentTypeDetector


class TestDocumentTypeDetector:
    def setup_method(self):
        self.detector = DocumentTypeDetector()

    # L1: Filename patterns
    def test_dwg_extension_detected_as_vykres(self):
        category, confidence = self.detector.detect("drawing_01.dwg", "application/octet-stream")
        assert category == "vykres"
        assert confidence == 0.90

    def test_dxf_extension_detected_as_vykres(self):
        category, confidence = self.detector.detect("vykres_koleno.dxf", "application/octet-stream")
        assert category == "vykres"
        assert confidence == 0.90

    def test_faktura_filename_detected(self):
        category, confidence = self.detector.detect("faktura_2025_001.pdf", "application/pdf")
        assert category == "faktura"
        assert confidence == 0.90

    def test_atestace_filename_detected(self):
        category, confidence = self.detector.detect("atest_P235GH.pdf", "application/pdf")
        assert category == "atestace"
        assert confidence == 0.90

    def test_nabidka_filename_detected(self):
        category, confidence = self.detector.detect("nabidka_NAB-2025-001.pdf", "application/pdf")
        assert category == "nabidka"
        assert confidence == 0.90

    def test_objednavka_filename_detected(self):
        category, confidence = self.detector.detect("objednavka_123.pdf", "application/pdf")
        assert category == "objednavka"
        assert confidence == 0.90

    def test_wps_filename_detected(self):
        category, confidence = self.detector.detect("WPS_001_MIG.pdf", "application/pdf")
        assert category == "wps"
        assert confidence == 0.90

    def test_protokol_filename_detected(self):
        category, confidence = self.detector.detect("protokol_zkousky.pdf", "application/pdf")
        assert category == "protokol"
        assert confidence == 0.90

    # L2: MIME type
    def test_acad_mime_detected_as_vykres(self):
        category, confidence = self.detector.detect("file.bin", "application/acad")
        assert category == "vykres"
        assert confidence == 0.85

    def test_dxf_mime_detected_as_vykres(self):
        category, confidence = self.detector.detect("file.bin", "application/dxf")
        assert category == "vykres"
        assert confidence == 0.85

    # L3: OCR text patterns
    def test_ocr_dn_pn_detected_as_vykres(self):
        category, confidence = self.detector.detect(
            "scan.pdf", "application/pdf",
            ocr_text="Koleno DN200 PN16 materiál P235GH"
        )
        assert category == "vykres"
        assert confidence == 0.75

    def test_ocr_ico_splatnost_detected_as_faktura(self):
        category, confidence = self.detector.detect(
            "scan.pdf", "application/pdf",
            ocr_text="IČO: 04856562 splatnost 14 dní"
        )
        assert category == "faktura"
        assert confidence == 0.75

    def test_ocr_en10204_detected_as_atestace(self):
        category, confidence = self.detector.detect(
            "cert.pdf", "application/pdf",
            ocr_text="Certifikát dle EN 10204 3.1"
        )
        assert category == "atestace"
        assert confidence == 0.75

    def test_ocr_wps_detected(self):
        category, confidence = self.detector.detect(
            "doc.pdf", "application/pdf",
            ocr_text="Svářečský postup WPS č. 001"
        )
        assert category == "wps"
        assert confidence == 0.75

    # Default fallback
    def test_unknown_file_defaults_to_ostatni(self):
        category, confidence = self.detector.detect("readme.txt", "text/plain")
        assert category == "ostatni"
        assert confidence == 0.50

    def test_generic_pdf_defaults_to_ostatni(self):
        category, confidence = self.detector.detect("document.pdf", "application/pdf")
        assert category == "ostatni"
        assert confidence == 0.50

    # Priority: L1 > L2 > L3
    def test_filename_takes_priority_over_ocr(self):
        category, confidence = self.detector.detect(
            "faktura_123.pdf", "application/pdf",
            ocr_text="DN200 PN16 koleno"
        )
        assert category == "faktura"
        assert confidence == 0.90  # L1 confidence
