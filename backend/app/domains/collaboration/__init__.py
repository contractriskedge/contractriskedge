"""Enterprise Collaboration Layer — threaded discussions, evidence annotations, clause comments, review mentions, escalation chat context, approval discussion history.

Contracts are collaborative systems. This increases organizational stickiness massively.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CommentType(str, Enum):
    DISCUSSION = "discussion"           # Threaded discussion
    ANNOTATION = "annotation"           # Evidence annotation
    CLAUSE_COMMENT = "clause_comment"   # Specific clause comment
    REVIEW_NOTE = "review_note"         # Internal review note
    MENTION = "mention"                 # @mention notification
    ESCALATION = "escalation"           # Escalation context
    APPROVAL = "approval"               # Approval decision discussion


@dataclass
class Comment:
    """A single comment in the collaboration system."""
    comment_id: str
    review_id: str
    author_id: str
    author_name: str
    comment_type: CommentType
    body: str
    parent_id: str | None = None  # For threaded replies
    mentions: list[str] = field(default_factory=list)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    edited_at: str | None = None
    resolved: bool = False


@dataclass
class Annotation:
    """An annotation on specific evidence or clause text."""
    annotation_id: str
    review_id: str
    chunk_id: str
    author_id: str
    text: str  # The annotated text
    comment: str  # The annotation comment
    annotation_type: str  # question, concern, suggestion, approval
    start_offset: int = 0
    end_offset: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved: bool = False


@dataclass
class CollaborationThread:
    """A threaded discussion around a review item."""
    thread_id: str
    review_id: str
    title: str
    comments: list[Comment] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_resolved: bool = False


@dataclass
class CollaborationService:
    """Enterprise collaboration layer for contract review workflows.

    Provides:
    - Threaded discussions on reviews and findings
    - Evidence annotations (comment on specific text)
    - Clause-level comments
    - @mentions with notifications
    - Escalation chat context (full discussion history)
    - Approval discussion history
    """

    _threads: dict[str, CollaborationThread] = field(default_factory=dict)
    _comments: dict[str, Comment] = field(default_factory=dict)
    _annotations: dict[str, Annotation] = field(default_factory=dict)

    def create_thread(self, review_id: str, title: str, author_id: str) -> CollaborationThread:
        """Create a new discussion thread on a review."""
        thread = CollaborationThread(
            thread_id=str(uuid.uuid4()),
            review_id=review_id,
            title=title,
            participants=[author_id],
        )
        self._threads[thread.thread_id] = thread
        return thread

    def add_comment(self, thread_id: str, author_id: str, author_name: str, body: str, parent_id: str | None = None) -> Comment:
        """Add a comment to a thread."""
        thread = self._threads.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        mentions = [w.strip("@") for w in body.split() if w.startswith("@")]

        comment = Comment(
            comment_id=str(uuid.uuid4()),
            review_id=thread.review_id,
            author_id=author_id,
            author_name=author_name,
            comment_type=CommentType.DISCUSSION,
            body=body,
            parent_id=parent_id,
            mentions=mentions,
        )
        self._comments[comment.comment_id] = comment
        thread.comments.append(comment)
        if author_id not in thread.participants:
            thread.participants.append(author_id)

        return comment

    def add_annotation(self, review_id: str, chunk_id: str, author_id: str, text: str, comment: str, annotation_type: str = "comment") -> Annotation:
        """Add an annotation on specific evidence text."""
        annotation = Annotation(
            annotation_id=str(uuid.uuid4()),
            review_id=review_id,
            chunk_id=chunk_id,
            author_id=author_id,
            text=text,
            comment=comment,
            annotation_type=annotation_type,
        )
        self._annotations[annotation.annotation_id] = annotation
        return annotation

    def get_thread(self, thread_id: str) -> CollaborationThread | None:
        """Get a discussion thread with all comments."""
        return self._threads.get(thread_id)

    def get_review_threads(self, review_id: str) -> list[CollaborationThread]:
        """Get all threads for a review."""
        return [t for t in self._threads.values() if t.review_id == review_id]

    def get_review_annotations(self, review_id: str) -> list[Annotation]:
        """Get all annotations for a review."""
        return [a for a in self._annotations.values() if a.review_id == review_id]

    def get_escalation_context(self, review_id: str) -> dict[str, Any]:
        """Get full escalation context including all discussions and annotations."""
        threads = self.get_review_threads(review_id)
        annotations = self.get_review_annotations(review_id)

        all_comments = []
        for thread in threads:
            for comment in thread.comments:
                all_comments.append({
                    "author": comment.author_name,
                    "body": comment.body,
                    "created_at": comment.created_at,
                    "mentions": comment.mentions,
                })

        return {
            "review_id": review_id,
            "thread_count": len(threads),
            "comment_count": len(all_comments),
            "annotation_count": len(annotations),
            "participants": list(set(
                p for t in threads for p in t.participants
            )),
            "comments": sorted(all_comments, key=lambda c: c["created_at"]),
            "annotations": [
                {"text": a.text, "comment": a.comment, "type": a.annotation_type}
                for a in annotations
            ],
        }

    def resolve_thread(self, thread_id: str) -> None:
        """Mark a thread as resolved."""
        thread = self._threads.get(thread_id)
        if thread:
            thread.is_resolved = True

    def resolve_annotation(self, annotation_id: str) -> None:
        """Mark an annotation as resolved."""
        annotation = self._annotations.get(annotation_id)
        if annotation:
            annotation.resolved = True

    def get_collaboration_summary(self, review_id: str) -> dict[str, Any]:
        """Get collaboration summary for a review."""
        threads = self.get_review_threads(review_id)
        annotations = self.get_review_annotations(review_id)
        total_comments = sum(len(t.comments) for t in threads)
        unresolved = sum(1 for t in threads if not t.is_resolved)

        return {
            "review_id": review_id,
            "threads": len(threads),
            "comments": total_comments,
            "annotations": len(annotations),
            "unresolved_threads": unresolved,
            "participants": list(set(
                p for t in threads for p in t.participants
            )),
        }


# ── Global singleton ───────────────────────────────────────────────

collaboration_service = CollaborationService()
