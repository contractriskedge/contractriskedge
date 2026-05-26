"""Word-level diff engine using diff-match-patch for redline comparisons.

Provides word-level diff computation between original and proposed clause
text, classifying each word as insert, delete, or equal for structured
redline output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DiffOperation(str, Enum):
    """Type of diff operation for a word or token."""

    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"

    def __str__(self) -> str:
        return self.value


@dataclass
class WordDiff:
    """A single word-level diff operation."""

    operation: DiffOperation
    text: str
    position: int = 0


class DiffEngineError(Exception):
    """Raised when diff computation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DiffEngine:
    """Word-level diff engine for comparing original and proposed text.

    Uses Google's diff-match-patch algorithm adapted for word-level
    comparison. Produces structured diff output suitable for rendering
    redline markup.

    Usage:
        engine = DiffEngine()
        word_diffs = engine.compute_word_diff(original, proposed)
        stats = engine.compute_diff_stats(word_diffs)
        html = engine.render_html(word_diffs)
    """

    def __init__(self) -> None:
        """Initialize the diff engine."""
        self._min_word_length: int = 1

    def compute_word_diff(
        self,
        original_text: str,
        proposed_text: str,
    ) -> List[WordDiff]:
        """Compute a word-level diff between original and proposed text.

        Uses a simplified LCS-based word diff algorithm. Each word is
        classified as equal, inserted, or deleted.

        Args:
            original_text: The original clause text.
            proposed_text: The proposed (redlined) clause text.

        Returns:
            List of WordDiff objects representing the diff.

        Raises:
            DiffEngineError: If either input is empty.
        """
        if not original_text.strip() and not proposed_text.strip():
            raise DiffEngineError("Both original and proposed text are empty")

        original_words = self._tokenize(original_text)
        proposed_words = self._tokenize(proposed_text)

        diffs = self._compute_lcs_diff(original_words, proposed_words)
        return self._merge_adjacent(diffs)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Split text into word tokens, preserving whitespace.

        Args:
            text: The text to tokenize.

        Returns:
            List of word and whitespace tokens.
        """
        tokens: List[str] = []
        current_word: List[str] = []
        current_ws: List[str] = []

        for char in text:
            if char.isspace():
                if current_word:
                    tokens.append("".join(current_word))
                    current_word = []
                current_ws.append(char)
            else:
                if current_ws:
                    tokens.append("".join(current_ws))
                    current_ws = []
                current_word.append(char)

        if current_word:
            tokens.append("".join(current_word))
        if current_ws:
            tokens.append("".join(current_ws))

        return tokens

    def _compute_lcs_diff(
        self,
        original: List[str],
        proposed: List[str],
    ) -> List[WordDiff]:
        """Compute diff using longest common subsequence algorithm.

        Args:
            original: Original word tokens.
            proposed: Proposed word tokens.

        Returns:
            List of WordDiff operations.
        """
        m, n = len(original), len(proposed)

        # Build LCS table
        lcs_table = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if original[i - 1] == proposed[j - 1]:
                    lcs_table[i][j] = lcs_table[i - 1][j - 1] + 1
                else:
                    lcs_table[i][j] = max(
                        lcs_table[i - 1][j], lcs_table[i][j - 1]
                    )

        # Backtrack to build diff
        diffs: List[WordDiff] = []
        i, j = m, n
        temp_diffs: List[WordDiff] = []

        while i > 0 or j > 0:
            if i > 0 and j > 0 and original[i - 1] == proposed[j - 1]:
                temp_diffs.append(WordDiff(
                    operation=DiffOperation.EQUAL,
                    text=original[i - 1],
                ))
                i -= 1
                j -= 1
            elif j > 0 and (i == 0 or lcs_table[i][j - 1] >= lcs_table[i - 1][j]):
                temp_diffs.append(WordDiff(
                    operation=DiffOperation.INSERT,
                    text=proposed[j - 1],
                ))
                j -= 1
            elif i > 0:
                temp_diffs.append(WordDiff(
                    operation=DiffOperation.DELETE,
                    text=original[i - 1],
                ))
                i -= 1

        diffs = list(reversed(temp_diffs))

        # Assign positions
        for idx, diff in enumerate(diffs):
            diff.position = idx

        return diffs

    @staticmethod
    def _merge_adjacent(diffs: List[WordDiff]) -> List[WordDiff]:
        """Merge adjacent diffs with the same operation.

        Args:
            diffs: List of WordDiff objects.

        Returns:
            Merged list with adjacent same-operation entries combined.
        """
        if not diffs:
            return []

        merged: List[WordDiff] = [diffs[0]]
        for diff in diffs[1:]:
            if diff.operation == merged[-1].operation:
                merged[-1].text += diff.text
            else:
                merged.append(diff)

        return merged

    def compute_diff_stats(
        self,
        diffs: List[WordDiff],
    ) -> Dict[str, int]:
        """Compute statistics from a word diff.

        Args:
            diffs: List of WordDiff objects.

        Returns:
            Dict with word_count, insertions, deletions, changes stats.
        """
        stats: Dict[str, int] = {
            "total_words": 0,
            "insertions": 0,
            "deletions": 0,
            "equal": 0,
            "changes": 0,
        }

        for diff in diffs:
            word_count = len(diff.text.split())
            stats["total_words"] += word_count

            if diff.operation == DiffOperation.INSERT:
                stats["insertions"] += word_count
                stats["changes"] += 1
            elif diff.operation == DiffOperation.DELETE:
                stats["deletions"] += word_count
                stats["changes"] += 1
            else:
                stats["equal"] += word_count

        return stats

    def compute_change_type(
        self,
        original_text: str,
        proposed_text: str,
        diffs: Optional[List[WordDiff]] = None,
    ) -> str:
        """Determine the overall change type based on diff analysis.

        Args:
            original_text: The original text.
            proposed_text: The proposed text.
            diffs: Optional pre-computed diffs.

        Returns:
            Change type: 'insertion', 'deletion', 'modification', or 'rewrite'.
        """
        if not original_text.strip():
            return "insertion"
        if not proposed_text.strip():
            return "deletion"

        if diffs is None:
            diffs = self.compute_word_diff(original_text, proposed_text)

        stats = self.compute_diff_stats(diffs)

        # If most words changed, it's a rewrite
        total_changed = stats["insertions"] + stats["deletions"]
        total = stats["total_words"]

        if total == 0:
            return "modification"

        change_ratio = total_changed / total if total > 0 else 0

        if change_ratio > 0.7:
            return "rewrite"
        elif stats["insertions"] > 0 and stats["deletions"] > 0:
            return "modification"
        elif stats["insertions"] > 0:
            return "insertion"
        elif stats["deletions"] > 0:
            return "deletion"
        else:
            return "modification"

    def render_html(self, diffs: List[WordDiff]) -> str:
        """Render diff as HTML with visual markup.

        Args:
            diffs: List of WordDiff objects.

        Returns:
            HTML string with insertions in green and deletions in red.
        """
        parts: List[str] = []
        for diff in diffs:
            escaped_text = (
                diff.text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            if diff.operation == DiffOperation.INSERT:
                parts.append(
                    f'<span class="diff-insert" style="background-color: #e6ffe6; '
                    f'text-decoration: none;">{escaped_text}</span>'
                )
            elif diff.operation == DiffOperation.DELETE:
                parts.append(
                    f'<span class="diff-delete" style="background-color: #ffe6e6; '
                    f'text-decoration: line-through;">{escaped_text}</span>'
                )
            else:
                parts.append(escaped_text)

        return "".join(parts)

    def render_plain_text(self, diffs: List[WordDiff]) -> str:
        """Render diff as plain text with +/- markers.

        Args:
            diffs: List of WordDiff objects.

        Returns:
            Plain text diff with insertions prefixed by '+' and deletions by '-'.
        """
        lines: List[str] = []
        for diff in diffs:
            if diff.operation == DiffOperation.INSERT:
                lines.append(f"+ {diff.text}")
            elif diff.operation == DiffOperation.DELETE:
                lines.append(f"- {diff.text}")
            else:
                lines.append(f"  {diff.text}")
        return "\n".join(lines)

    def get_word_diff_summary(
        self,
        original_text: str,
        proposed_text: str,
    ) -> str:
        """Get a concise summary of the word-level differences.

        Args:
            original_text: The original text.
            proposed_text: The proposed text.

        Returns:
            A human-readable summary string.
        """
        diffs = self.compute_word_diff(original_text, proposed_text)
        stats = self.compute_diff_stats(diffs)
        change_type = self.compute_change_type(original_text, proposed_text, diffs)

        return (
            f"{change_type.title()}: {stats['deletions']} words removed, "
            f"{stats['insertions']} words added "
            f"({stats['changes']} change(s) across {stats['total_words']} total words)"
        )
