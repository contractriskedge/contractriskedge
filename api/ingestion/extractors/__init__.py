"""Document text extractors for the AI Contract Risk Analyzer.

Provides a unified interface for extracting text from various document
formats including PDF, DOCX, and scanned images via OCR.
"""

from ingestion.extractors.pdf_extractor import PdfExtractor
from ingestion.extractors.docx_extractor import DocxExtractor
from ingestion.extractors.ocr_pipeline import OcrPipeline
from ingestion.extractors.clause_segmenter import ClauseSegmenter
from ingestion.extractors.clause_hierarchy import ClauseHierarchyBuilder
from ingestion.extractors.models import ExtractionResult, ExtractedPage
from ingestion.extractors.edge_cases import EdgeCaseHandler

__all__ = [
    "PdfExtractor",
    "DocxExtractor",
    "OcrPipeline",
    "ClauseSegmenter",
    "ClauseHierarchyBuilder",
    "ExtractionResult",
    "ExtractedPage",
    "EdgeCaseHandler",
]
