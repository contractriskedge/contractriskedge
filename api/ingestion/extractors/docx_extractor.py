"""DOCX text extraction using python-docx with structural preservation.

Extracts text from Word documents while preserving document structure
including headings, lists, tables, and paragraph styles. Produces
page-like output compatible with the extraction pipeline.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from ingestion.extractors.models import (
    ExtractedPage,
    ExtractionMethod,
    ExtractionStatus,
    PageMetadata,
)

logger = logging.getLogger(__name__)


class DocxExtractionError(Exception):
    """Raised when DOCX extraction fails."""


class DocxExtractor:
    """Extracts text and structure from DOCX documents.

    Uses python-docx to parse .docx files, preserving headings,
    lists, tables, and paragraph formatting. Produces page-like
    output for compatibility with the rest of the pipeline.

    Attributes:
        chars_per_page: Approximate characters per virtual page (default 3000).
    """

    SUPPORTED_EXTENSIONS = {".docx", ".doc"}

    def __init__(self, chars_per_page: int = 3000) -> None:
        """Initialize the DOCX extractor.

        Args:
            chars_per_page: Target characters per virtual page.
        """
        self.chars_per_page = chars_per_page

    def extract(
        self,
        file_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[ExtractedPage]:
        """Extract text from a DOCX file, preserving document structure.

        Args:
            file_path: Path to the .docx file.
            options: Extraction options dict with optional keys:
                - include_tables: bool (default True)
                - include_headers: bool (default True)
                - preserve_formatting: bool (default True)

        Returns:
            List of ExtractedPage objects with structured content.

        Raises:
            DocxExtractionError: If extraction fails.
            FileNotFoundError: If the file does not exist.
        """
        options = options or {}

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"DOCX file not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise DocxExtractionError(
                f"Unsupported extension '{ext}'. Supported: {self.SUPPORTED_EXTENSIONS}"
            )

        include_tables = options.get("include_tables", True)
        include_headers = options.get("include_headers", True)
        preserve_formatting = options.get("preserve_formatting", True)

        logger.info(
            "Starting DOCX extraction: %s",
            os.path.basename(file_path),
        )
        start_time = time.time()

        try:
            from docx import Document
        except ImportError:
            raise DocxExtractionError(
                "python-docx is not installed. Install with: pip install python-docx"
            )

        try:
            doc = Document(file_path)
        except Exception as exc:
            raise DocxExtractionError(f"Failed to open DOCX file: {exc}") from exc

        # Extract document body content
        content_parts: List[Dict[str, Any]] = []
        current_section = {"type": "paragraph", "content": [], "heading_level": None}

        for element in doc.element.body:
            tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

            if tag == "p":
                # Paragraph
                para = self._find_paragraph(doc, element)
                if para is None:
                    continue

                text = para.text.strip()
                if not text:
                    continue

                style_name = para.style.name if para.style else "Normal"

                if style_name.startswith("Heading"):
                    # Flush current section
                    if current_section["content"]:
                        content_parts.append(dict(current_section))
                    level = int(style_name.replace("Heading ", "")) if style_name != "Heading" else 1
                    current_section = {
                        "type": "heading",
                        "content": [text],
                        "heading_level": level,
                    }
                elif style_name == "List Paragraph":
                    # Detect list item
                    try:
                        numPr = element.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr")
                        ilvl = numPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ilvl")
                        level = int(ilvl.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", 0)) if ilvl is not None else 0
                    except Exception:
                        level = 0
                    indent = "  " * level + "- "
                    current_section["type"] = "list"
                    current_section["content"].append(f"{indent}{text}")
                else:
                    current_section["content"].append(text)

            elif tag == "tbl" and include_tables:
                # Table
                if current_section["content"]:
                    content_parts.append(dict(current_section))
                    current_section = {"type": "paragraph", "content": [], "heading_level": None}

                table_content = self._extract_table(element)
                content_parts.append({"type": "table", "content": table_content})

        # Flush remaining content
        if current_section["content"]:
            content_parts.append(dict(current_section))

        # Convert content parts to virtual pages
        pages = self._build_virtual_pages(content_parts)

        # Extract document-level metadata
        total_chars = sum(len(p.text) for p in pages)
        processing_time = time.time() - start_time

        logger.info(
            "DOCX extraction complete: %s - %d virtual pages, %d chars in %.2fs",
            os.path.basename(file_path),
            len(pages),
            total_chars,
            processing_time,
        )

        return pages

    def _find_paragraph(
        self,
        doc: Any,
        element: Any,
    ) -> Any:
        """Find the python-docx Paragraph object for an XML element.

        Args:
            doc: The python-docx Document instance.
            element: The XML element to match.

        Returns:
            The matching Paragraph, or None.
        """
        for para in doc.paragraphs:
            if para._element is element:
                return para
        return None

    def _extract_table(self, table_element: Any) -> List[List[str]]:
        """Extract content from a DOCX table element.

        Args:
            table_element: The table XML element.

        Returns:
            List of rows, where each row is a list of cell strings.
        """
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        rows: List[List[str]] = []

        try:
            for tr in table_element.findall(f".//{ns}tr"):
                row: List[str] = []
                for tc in tr.findall(f"{ns}tc"):
                    cell_texts: List[str] = []
                    for p in tc.findall(f".//{ns}p"):
                        texts = [
                            t.text or ""
                            for t in p.findall(f".//{ns}t")
                        ]
                        cell_texts.append("".join(texts).strip())
                    row.append(" | ".join(cell_texts))
                rows.append(row)
        except Exception as exc:
            logger.warning("Failed to extract table: %s", exc)

        return rows

    def _build_virtual_pages(
        self,
        content_parts: List[Dict[str, Any]],
    ) -> List[ExtractedPage]:
        """Group extracted content into virtual pages.

        Since DOCX files don't have fixed pages, we create virtual
        pages based on character count.

        Args:
            content_parts: List of content sections.

        Returns:
            List of ExtractedPage objects.
        """
        pages: List[ExtractedPage] = []
        current_page_text: List[str] = []
        current_page_chars = 0
        page_number = 1
        tables_on_page: List[List[List[str]]] = []

        def flush_page() -> None:
            """Flush current page buffer into an ExtractedPage."""
            nonlocal page_number, current_page_text, current_page_chars, tables_on_page

            if current_page_text or tables_on_page:
                text = "\n\n".join(current_page_text)
                pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text=text,
                        method=ExtractionMethod.DOCX,
                        confidence=0.98,
                        status=ExtractionStatus.SUCCESS,
                        metadata=PageMetadata(
                            word_count=len(text.split()),
                            has_tables=len(tables_on_page) > 0,
                        ),
                        tables=list(tables_on_page),
                    )
                )
                page_number += 1
                current_page_text = []
                current_page_chars = 0
                tables_on_page = []

        for part in content_parts:
            part_type = part.get("type", "paragraph")
            content = part.get("content", [])

            if part_type == "heading":
                heading_level = part.get("heading_level", 1)
                prefix = "#" * heading_level + " "
                text = prefix + "\n".join(content) if isinstance(content, list) else str(content)

                if current_page_chars + len(text) > self.chars_per_page and current_page_text:
                    flush_page()
                current_page_text.append(text)
                current_page_chars += len(text)

            elif part_type == "list":
                text = "\n".join(content) if isinstance(content, list) else str(content)
                if current_page_chars + len(text) > self.chars_per_page and current_page_text:
                    flush_page()
                current_page_text.append(text)
                current_page_chars += len(text)

            elif part_type == "paragraph":
                for para_text in content if isinstance(content, list) else [content]:
                    if current_page_chars + len(para_text) > self.chars_per_page and current_page_text:
                        flush_page()
                    current_page_text.append(para_text)
                    current_page_chars += len(para_text)

            elif part_type == "table":
                table_content = content
                if isinstance(table_content, list) and table_content:
                    table_str = "\n".join(
                        " | ".join(row) for row in table_content
                    )
                    if current_page_chars + len(table_str) > self.chars_per_page and current_page_text:
                        flush_page()
                    tables_on_page.append(
                        [[str(cell) for cell in row] for row in table_content]
                    )
                    current_page_text.append(f"[Table: {len(table_content)} rows x {max(len(r) for r in table_content)} cols]")
                    current_page_chars += len(table_str)

        # Flush last page
        flush_page()

        if not pages:
            pages.append(
                ExtractedPage(
                    page_number=1,
                    text="",
                    method=ExtractionMethod.DOCX,
                    confidence=0.0,
                    status=ExtractionStatus.FAILED,
                    metadata=PageMetadata(),
                )
            )

        return pages
