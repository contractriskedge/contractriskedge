"""XML manipulation for Word tracked changes (<w:ins> and <w:del> elements).

Provides utilities for creating and managing native Word tracked changes
at the XML level, enabling programmatic redline generation in DOCX files.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from lxml import etree

logger = logging.getLogger(__name__)

# XML namespaces used by WordprocessingML
NAMESPACES = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
}

NSMAP = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
}

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _register_namespaces() -> None:
    """Register XML namespaces for lxml."""
    for prefix, uri in NSMAP.items():
        etree.register_namespace(prefix, uri)


_register_namespaces()


@dataclass
class TrackedChange:
    """Represents a single tracked change in a Word document.

    Can be either an insertion (<w:ins>) or deletion (<w:del>).
    """

    change_type: str  # "insertion" or "deletion"
    author: str
    date: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    comment: str = ""


class TrackedChangeManager:
    """Manages creation of Word tracked changes at the XML level.

    Handles the complex XML structure required for native Word
    tracked changes, including proper ID generation, author tracking,
    and datetime formatting.

    Usage:
        manager = TrackedChangeManager()
        ins_elem = manager.create_insertion_xml(
            "New text here", author="user@example.com"
        )
        del_elem = manager.create_deletion_xml(
            "Old text here", author="user@example.com"
        )
    """

    def __init__(self, default_author: str = "AI Contract Risk Analyzer") -> None:
        """Initialize the tracked change manager.

        Args:
            default_author: Default author name for tracked changes.
        """
        self._default_author = default_author
        self._change_counter: int = 0

    def _next_id(self) -> int:
        """Generate a sequential change ID.

        Returns:
            A unique integer ID for the tracked change.
        """
        self._change_counter += 1
        return self._change_counter

    @staticmethod
    def _format_datetime(dt: Optional[datetime] = None) -> str:
        """Format a datetime for Word's tracked change format.

        Args:
            dt: The datetime to format. Defaults to now.

        Returns:
            Formatted datetime string in ISO 8601 format.
        """
        if dt is None:
            dt = datetime.utcnow()
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def create_insertion_xml(
        self,
        text: str,
        author: Optional[str] = None,
        date: Optional[datetime] = None,
        change_id: Optional[int] = None,
    ) -> etree.Element:
        """Create XML element for a tracked insertion (<w:ins>).

        Args:
            text: The inserted text content.
            author: Author of the change. Defaults to default_author.
            date: Date of the change. Defaults to now.
            change_id: Optional explicit change ID.

        Returns:
            An lxml Element representing the <w:ins> structure.
        """
        author = author or self._default_author
        date = date or datetime.utcnow()
        change_id = change_id or self._next_id()

        # Create <w:ins> element
        ins = etree.Element(f"{{{W_NS}}}ins")
        ins.set(f"{{{W_NS}}}id", str(change_id))
        ins.set(f"{{{W_NS}}}author", author)
        ins.set(f"{{{W_NS}}}date", self._format_datetime(date))

        # Create <w:r> (run) inside <w:ins>
        run = etree.SubElement(ins, f"{{{W_NS}}}r")

        # Create <w:rPr> (run properties)
        rpr = etree.SubElement(run, f"{{{W_NS}}}rPr")

        # Add underline formatting for insertions (Word convention)
        u = etree.SubElement(rpr, f"{{{W_NS}}}u")
        u.set(f"{{{W_NS}}}val", "single")

        # Add color formatting for insertions
        color = etree.SubElement(rpr, f"{{{W_NS}}}color")
        color.set(f"{{{W_NS}}}val", "008000")  # Green

        # Create <w:t> (text) element
        t = etree.SubElement(run, f"{{{W_NS}}}t")
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = text

        return ins

    def create_deletion_xml(
        self,
        text: str,
        author: Optional[str] = None,
        date: Optional[datetime] = None,
        change_id: Optional[int] = None,
    ) -> etree.Element:
        """Create XML element for a tracked deletion (<w:del>).

        Args:
            text: The deleted text content.
            author: Author of the change. Defaults to default_author.
            date: Date of the change. Defaults to now.
            change_id: Optional explicit change ID.

        Returns:
            An lxml Element representing the <w:del> structure.
        """
        author = author or self._default_author
        date = date or datetime.utcnow()
        change_id = change_id or self._next_id()

        # Create <w:del> element
        del_elem = etree.Element(f"{{{W_NS}}}del")
        del_elem.set(f"{{{W_NS}}}id", str(change_id))
        del_elem.set(f"{{{W_NS}}}author", author)
        del_elem.set(f"{{{W_NS}}}date", self._format_datetime(date))

        # Create <w:r> (run) inside <w:del>
        run = etree.SubElement(del_elem, f"{{{W_NS}}}r")

        # Create <w:rPr> (run properties)
        rpr = etree.SubElement(run, f"{{{W_NS}}}rPr")

        # Add strikethrough formatting for deletions (Word convention)
        strike = etree.SubElement(rpr, f"{{{W_NS}}}strike")
        strike.set(f"{{{W_NS}}}val", "true")

        # Add color formatting for deletions
        color = etree.SubElement(rpr, f"{{{W_NS}}}color")
        color.set(f"{{{W_NS}}}val", "FF0000")  # Red

        # Create <w:delText> element (not <w:t> for deletions)
        del_text = etree.SubElement(run, f"{{{W_NS}}}delText")
        del_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        del_text.text = text

        return del_elem

    def create_paragraph_xml(
        self,
        original_text: str,
        proposed_text: str,
        author: Optional[str] = None,
    ) -> etree.Element:
        """Create a paragraph XML with tracked changes applied.

        Takes original and proposed text, computes word-level diff,
        and wraps changes in appropriate <w:ins> and <w:del> elements.

        Args:
            original_text: The original (to be replaced) text.
            proposed_text: The proposed (new) text.
            author: Author of the changes.

        Returns:
            An lxml Element representing the paragraph with tracked changes.
        """
        author = author or self._default_author

        # Create <w:p> element
        p = etree.Element(f"{{{W_NS}}}p")

        # For simplicity, create deletion of original text and insertion of proposed text
        if original_text.strip():
            del_elem = self.create_deletion_xml(original_text, author=author)
            p.append(del_elem)

        if proposed_text.strip():
            ins_elem = self.create_insertion_xml(proposed_text, author=author)
            p.append(ins_elem)

        return p

    def add_tracked_change_to_paragraph(
        self,
        paragraph: Any,
        change: TrackedChange,
    ) -> None:
        """Add a tracked change to an existing python-docx paragraph.

        Manipulates the XML of a python-docx paragraph to inject
        tracked changes.

        Args:
            paragraph: A python-docx Paragraph object.
            change: The TrackedChange to apply.
        """
        # Access the paragraph's XML element
        p_elem = paragraph._element  # type: ignore[attr-defined]

        if change.change_type == "insertion":
            change_elem = self.create_insertion_xml(
                text=change.text,
                author=change.author or self._default_author,
                date=change.date,
            )
        else:
            change_elem = self.create_deletion_xml(
                text=change.text,
                author=change.author or self._default_author,
                date=change.date,
            )

        # Append the change element to the paragraph
        p_elem.append(change_elem)

    def create_run_with_tracked_change(
        self,
        paragraph: Any,
        text: str,
        change_type: str,
        author: Optional[str] = None,
    ) -> Any:
        """Create a new run with tracked change markup in a paragraph.

        Args:
            paragraph: A python-docx Paragraph object.
            text: The text content.
            change_type: 'insertion' or 'deletion'.
            author: Author of the change.

        Returns:
            The created python-docx Run object.
        """
        from docx.oxml import OxmlElement
        from docx.text.run import Run

        author = author or self._default_author
        change_id = self._next_id()

        if change_type == "insertion":
            # Create <w:ins> wrapper
            ins_elem = OxmlElement("w:ins")
            ins_elem.set(f"{{{W_NS}}}id", str(change_id))
            ins_elem.set(f"{{{W_NS}}}author", author)
            ins_elem.set(f"{{{W_NS}}}date", self._format_datetime())

            # Create run inside insertion
            run_elem = OxmlElement("w:r")
            rpr = OxmlElement("w:rPr")
            u = OxmlElement("w:u")
            u.set(f"{{{W_NS}}}val", "single")
            rpr.append(u)
            color = OxmlElement("w:color")
            color.set(f"{{{W_NS}}}val", "008000")
            rpr.append(color)
            run_elem.append(rpr)

            t = OxmlElement("w:t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = text
            run_elem.append(t)
            ins_elem.append(run_elem)

            paragraph._element.append(ins_elem)  # type: ignore[attr-defined]
            return Run(run_elem, paragraph)

        else:
            # Create <w:del> wrapper
            del_elem = OxmlElement("w:del")
            del_elem.set(f"{{{W_NS}}}id", str(change_id))
            del_elem.set(f"{{{W_NS}}}author", author)
            del_elem.set(f"{{{W_NS}}}date", self._format_datetime())

            run_elem = OxmlElement("w:r")
            rpr = OxmlElement("w:rPr")
            strike = OxmlElement("w:strike")
            strike.set(f"{{{W_NS}}}val", "true")
            rpr.append(strike)
            color = OxmlElement("w:color")
            color.set(f"{{{W_NS}}}val", "FF0000")
            rpr.append(color)
            run_elem.append(rpr)

            del_text = OxmlElement("w:delText")
            del_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            del_text.text = text
            run_elem.append(del_text)
            del_elem.append(run_elem)

            paragraph._element.append(del_elem)  # type: ignore[attr-defined]
            return Run(run_elem, paragraph)
