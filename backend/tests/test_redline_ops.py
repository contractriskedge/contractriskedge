"""Tests for redline operation classification and diff building."""

from app.domains.review.redline_ops import (
    RedlineOperation,
    build_word_diff,
    infer_operation,
)


def test_missing_governing_law_inferred_as_insert():
    original = (
        "SAMPLE FORM OF EMPLOYMENT CONTRACT CONTRACT OF EMPLOYMENT KNOW ALL MEN "
        "BY THESE PRESENTS: This Contract is executed at Makati City between ABC INC."
    )
    proposed = (
        "GOVERNING LAW:\nThis Contract of Employment shall be governed by the laws "
        "of the Republic of the Philippines."
    )
    op = infer_operation(original, proposed, clause_type="governing_law")
    assert op == RedlineOperation.INSERT


def test_insert_diff_shows_only_additions():
    proposed = "GOVERNING LAW: This Agreement shall be governed by the laws of the Philippines."
    segments = build_word_diff(RedlineOperation.INSERT, "", proposed)
    assert all(s["tag"] == "insert" for s in segments)
    assert "GOVERNING" in segments[0]["text"]


def test_modification_diff_highlights_changed_words():
    original = "The liability cap shall be unlimited for all damages."
    proposed = "The liability cap shall be limited to two times annual fees."
    segments = build_word_diff(RedlineOperation.MODIFICATION, original, proposed)
    tags = {s["tag"] for s in segments}
    assert "delete" in tags and "insert" in tags


def test_modified_clause_keeps_heading_and_unchanged_sentence_normal():
    original = (
        "10. Limitation of Liability\n"
        "Except for liability arising from gross negligence, willful misconduct, "
        "or breach of confidentiality obligations, neither party shall be liable "
        "for indirect damages."
    )
    proposed = (
        "10. Limitation of Liability\n"
        "Except for liability arising from gross negligence, willful misconduct, "
        "or breach of confidentiality obligations, neither party shall be liable "
        "for indirect, incidental, consequential, special, or punitive damages."
    )

    segments = build_word_diff(RedlineOperation.MODIFICATION, original, proposed)

    assert segments[0] == {"tag": "equal", "text": "10. Limitation of Liability\n"}
    assert any(s["tag"] == "equal" and "Except for liability" in s["text"] for s in segments)
    assert any(
        s["tag"] == "insert" and "incidental, consequential" in s["text"]
        for s in segments
    )


def test_delete_diff_renders_complete_removed_text():
    original = "arising out of or in connection with"
    segments = build_word_diff(RedlineOperation.DELETE, original, "")
    assert segments == [{"tag": "delete", "text": original}]
