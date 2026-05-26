"""Tests for OCR and document extraction pipeline."""

from __future__ import annotations

import pytest
from app.domains.extraction.parsers import (
    PDFParser, DOCXParser, TXTParser, ParserRegistry,
    EncryptedPDFError, CorruptedDocumentError,
)
from app.domains.extraction.quality import QualityEvaluator
from app.domains.extraction.normalizer import normalize_text


class TestPDFParser:
    """Verify PDF text extraction."""

    def setup_method(self):
        self.parser = PDFParser()

    def test_detect_pdf_by_mime(self):
        assert self.parser.supports("application/pdf", b"%PDF-1.4")

    def test_detect_pdf_by_magic_bytes(self):
        assert self.parser.supports("unknown", b"%PDF-1.4\n...")

    def test_reject_non_pdf(self):
        assert not self.parser.supports("text/plain", b"hello world")

    def test_detect_type(self):
        assert self.parser.detect_type(b"%PDF-1.4") == "pdf"


class TestDOCXParser:
    """Verify DOCX text extraction."""

    def setup_method(self):
        self.parser = DOCXParser()

    def test_supports_docx_mime(self):
        assert self.parser.supports(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"PK\x03\x04",
        )

    def test_detect_type(self):
        assert self.parser.detect_type(b"PK\x03\x04") == "docx"


class TestTXTParser:
    """Verify TXT text extraction."""

    def setup_method(self):
        self.parser = TXTParser()

    def test_supports_txt(self):
        assert self.parser.supports("text/plain", b"hello world")

    def test_detect_type(self):
        assert self.parser.detect_type(b"hello") == "txt"


class TestParserRegistry:
    """Verify parser auto-detection."""

    def setup_method(self):
        self.registry = ParserRegistry()

    def test_get_pdf_parser(self):
        parser = self.registry.get_parser("application/pdf", b"%PDF-1.4")
        assert parser is not None
        assert parser.detect_type(b"%PDF") == "pdf"

    def test_get_txt_parser(self):
        parser = self.registry.get_parser("text/plain", b"hello")
        assert parser is not None

    def test_get_unknown_parser(self):
        parser = self.registry.get_parser("application/octet-stream", b"data")
        assert parser is None


class TestQualityScoring:
    """Verify extraction quality evaluation."""

    def setup_method(self):
        self.evaluator = QualityEvaluator()

    def test_perfect_quality_passes(self):
        from app.domains.extraction.parsers import ExtractedPage, ExtractionResult
        result = ExtractionResult(
            pages=[
                ExtractedPage(page_number=1, text="Hello world " * 100, char_count=1200, word_count=200, confidence=0.95),
                ExtractedPage(page_number=2, text="Second page " * 100, char_count=1100, word_count=200, confidence=0.95),
            ],
            total_pages=2, total_chars=2300, method="test",
        )
        quality = self.evaluator.evaluate(result)
        assert quality.is_acceptable
        assert quality.overall_score > 0.7

    def test_blank_pages_fail(self):
        from app.domains.extraction.parsers import ExtractedPage, ExtractionResult
        result = ExtractionResult(
            pages=[
                ExtractedPage(page_number=1, text="", char_count=0, word_count=0, confidence=0.1),
                ExtractedPage(page_number=2, text="", char_count=0, word_count=0, confidence=0.1),
            ],
            total_pages=2, total_chars=0, method="test",
        )
        quality = self.evaluator.evaluate(result)
        assert not quality.is_acceptable
        assert quality.rejection_reason is not None

    def test_low_confidence_fails(self):
        from app.domains.extraction.parsers import ExtractedPage, ExtractionResult
        result = ExtractionResult(
            pages=[
                ExtractedPage(page_number=1, text="garbage" * 100, char_count=700, word_count=100, confidence=0.2),
                ExtractedPage(page_number=2, text="garbage" * 100, char_count=700, word_count=100, confidence=0.2),
            ],
            total_pages=2, total_chars=1400, method="test",
        )
        quality = self.evaluator.evaluate(result)
        assert not quality.is_acceptable
        assert "confidence" in (quality.rejection_reason or "").lower()

    def test_no_pages_fails(self):
        from app.domains.extraction.parsers import ExtractionResult
        result = ExtractionResult(pages=[], method="test")
        quality = self.evaluator.evaluate(result)
        assert not quality.is_acceptable
        assert "No pages" in (quality.rejection_reason or "")


class TestTextNormalization:
    """Verify text normalization pipeline."""

    def test_unicode_normalization(self):
        text = "café résumé"
        normalized = normalize_text(text)
        assert "café" in normalized

    def test_line_ending_normalization(self):
        text = "line1\r\nline2\rline3"
        normalized = normalize_text(text)
        assert normalized.count("\n") == 2

    def test_ocr_artifact_removal(self):
        text = "Good text\n@@@@@@@\nMore good text"
        normalized = normalize_text(text)
        assert "@@@@@@@" not in normalized

    def test_whitespace_collapse(self):
        text = "hello     world    test"
        normalized = normalize_text(text)
        assert "     " not in normalized

    def test_control_char_removal(self):
        text = "hello\x00world\x01test"
        normalized = normalize_text(text)
        assert "\x00" not in normalized
        assert "\x01" not in normalized

    def test_encoding_repair(self):
        text = "\x93Smart quotes\x94"
        normalized = normalize_text(text)
        assert "\x93" not in normalized
        assert '"' in normalized or "'" in normalized


class TestTenantIsolation:
    """Verify extraction data is tenant-scoped."""

    def test_storage_key_contains_tenant(self):
        from app.integrations.storage.s3 import storage_service
        key_a = storage_service.build_object_key("tenant-alpha", "doc.pdf")
        key_b = storage_service.build_object_key("tenant-beta", "doc.pdf")
        assert "tenant-alpha" in key_a
        assert "tenant-beta" in key_b
        assert key_a != key_b
