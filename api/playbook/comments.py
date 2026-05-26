"""Clause-level commenting with @mention notifications.

Provides threaded comments anchored to specific clauses within
contracts, with @mention support and notification delivery.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CommentStatus(str, Enum):
    """Status of a comment thread."""

    OPEN = "open"
    RESOLVED = "resolved"


@dataclass
class Comment:
    """A single comment or reply in a thread."""

    comment_id: str = ""
    contract_id: str = ""
    clause_id: str = ""
    thread_id: str = ""
    parent_id: str = ""  # Empty for top-level, set for replies
    author_id: str = ""
    author_name: str = ""
    content: str = ""
    mentions: List[str] = field(default_factory=list)
    status: CommentStatus = CommentStatus.OPEN
    resolved_by: str = ""
    resolved_at: str = ""
    created_at: str = ""
    updated_at: str = ""


class CommentEngine:
    """Threaded commenting system anchored to contract clauses.

    Supports @mentions with notification routing and resolution tracking.

    Usage:
        engine = CommentEngine()
        comment = engine.add_comment(
            contract_id="...", clause_id="...",
            author_id="user-1", content="Needs review @user-2",
        )
        reply = engine.add_reply(comment.thread_id, "user-3", "Agreed")
    """

    def __init__(self) -> None:
        """Initialize the comment engine."""
        self._comments: Dict[str, Comment] = {}
        self._threads: Dict[str, List[str]] = {}  # thread_id -> [comment_ids]

    def add_comment(
        self,
        contract_id: str,
        clause_id: str,
        author_id: str,
        author_name: str,
        content: str,
    ) -> Comment:
        """Add a top-level comment to a clause.

        Args:
            contract_id: Contract identifier.
            clause_id: Clause identifier.
            author_id: User ID of the author.
            author_name: Display name of the author.
            content: Comment content with optional @mentions.

        Returns:
            The created Comment.
        """
        now = datetime.utcnow().isoformat() + "Z"
        thread_id = str(uuid.uuid4())
        mentions = self._extract_mentions(content)

        comment = Comment(
            comment_id=str(uuid.uuid4()),
            contract_id=contract_id,
            clause_id=clause_id,
            thread_id=thread_id,
            author_id=author_id,
            author_name=author_name,
            content=content,
            mentions=mentions,
            created_at=now,
            updated_at=now,
        )

        self._comments[comment.comment_id] = comment
        self._threads[thread_id] = [comment.comment_id]

        if mentions:
            logger.info(
                "Comment %s by %s @mentioned: %s",
                comment.comment_id[:8], author_id, mentions,
            )

        return comment

    def add_reply(
        self,
        thread_id: str,
        author_id: str,
        author_name: str,
        content: str,
    ) -> Optional[Comment]:
        """Add a reply to an existing comment thread.

        Args:
            thread_id: The thread to reply to.
            author_id: User ID of the author.
            author_name: Display name of the author.
            content: Reply content.

        Returns:
            The created Comment or None if thread not found.
        """
        if thread_id not in self._threads:
            return None

        now = datetime.utcnow().isoformat() + "Z"
        parent_id = self._threads[thread_id][-1]  # Reply to last comment
        mentions = self._extract_mentions(content)

        comment = Comment(
            comment_id=str(uuid.uuid4()),
            thread_id=thread_id,
            parent_id=parent_id,
            author_id=author_id,
            author_name=author_name,
            content=content,
            mentions=mentions,
            created_at=now,
            updated_at=now,
        )

        self._comments[comment.comment_id] = comment
        self._threads[thread_id].append(comment.comment_id)

        return comment

    def resolve_thread(self, thread_id: str, resolved_by: str) -> bool:
        """Mark a comment thread as resolved.

        Args:
            thread_id: The thread to resolve.
            resolved_by: User ID resolving the thread.

        Returns:
            True if resolved, False if not found.
        """
        if thread_id not in self._threads:
            return False

        now = datetime.utcnow().isoformat() + "Z"
        for cid in self._threads[thread_id]:
            comment = self._comments.get(cid)
            if comment:
                comment.status = CommentStatus.RESOLVED
                comment.resolved_by = resolved_by
                comment.resolved_at = now

        return True

    def get_thread(self, thread_id: str) -> List[Comment]:
        """Get all comments in a thread.

        Args:
            thread_id: The thread identifier.

        Returns:
            List of comments in chronological order.
        """
        comment_ids = self._threads.get(thread_id, [])
        return [self._comments[cid] for cid in comment_ids if cid in self._comments]

    def get_clause_comments(self, clause_id: str) -> List[Comment]:
        """Get all comments for a specific clause.

        Args:
            clause_id: The clause identifier.

        Returns:
            List of top-level comments (not replies).
        """
        return [
            c for c in self._comments.values()
            if c.clause_id == clause_id and not c.parent_id
        ]

    def get_contract_comments(self, contract_id: str) -> List[Comment]:
        """Get all comments for a contract.

        Args:
            contract_id: The contract identifier.

        Returns:
            List of all comments.
        """
        return [
            c for c in self._comments.values()
            if c.contract_id == contract_id
        ]

    @staticmethod
    def _extract_mentions(text: str) -> List[str]:
        """Extract @mentions from text.

        Args:
            text: Text to search for mentions.

        Returns:
            List of mentioned usernames.
        """
        import re
        return re.findall(r'@(\w+)', text)
