#!/usr/bin/env python3
"""
Standalone test script for the new Locate system.
Tests all the new features without needing the server running.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Test data
CONTRACT_TEXT = """MASTER SERVICES AGREEMENT

1. Services Provided
Provider shall deliver the services described in Exhibit A.

2. Subscription Fees and Auto-Renewal
Customer shall pay all fees within 30 days of invoice.
This Agreement shall automatically renew for successive one-year periods.

3. Data and Privacy
All personal data shall be processed in accordance with GDPR.

4. Intellectual Property
All intellectual property rights shall remain with the creating party.

5. Limitation of Liability
IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT DAMAGES.

6. Confidentiality
Each party agrees to maintain the confidentiality of proprietary information.

7. Termination
Either party may terminate this Agreement upon 30 days written notice.

8. Indemnification
Provider shall indemnify Customer against third-party IP claims.

9. Governing Law
This Agreement shall be governed by the laws of Delaware.
"""


def run_tests():
    """Run all tests for the new locate system."""
    from app.domains.review.locator import SectionParser, LocatorService
    from app.domains.review.router import _strip_synthetic_numbering
    from app.domains.review.locator.models import CLAUSE_RISK_RELATIONSHIPS, CLAUSE_INTENT

    passed = 0
    total = 0

    print("=" * 60)
    print("LOCATE SYSTEM TESTS")
    print("=" * 60)

    # Parse the contract
    parser = SectionParser()
    hierarchy = parser.parse(CONTRACT_TEXT)
    service = LocatorService(hierarchy, CONTRACT_TEXT)

    # Print section structure
    print("\n📋 Document Sections:")
    for s in hierarchy.sections:
        print(f"  §{s.section_id}: {s.title} (domain={s.legal_domain})")

    # ── TEST 1: Exact text match ──
    print("\n" + "=" * 60)
    print("TEST 1: MODIFY_EXISTING - Exact text match")
    print("=" * 60)
    total += 1
    r = service.locate(
        clause_type="limitation_of_liability",
        original_text="IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT DAMAGES.",
        proposed_text="Modified liability cap with exclusions.",
        operation="modification",
    )
    checks = [
        ("Status resolved", r.status.value == "resolved"),
        ("Anchor exact_text_span", r.anchor_type.value == "exact_text_span"),
        ("Confidence 0.97", r.confidence == 0.97),
        ("Section 5", r.section_id == "5"),
        ("Operation narrow_liability", r.clause_operation_type == "narrow_liability"),
        ("Action label NARROW", r.action_label == "NARROW"),
        ("Summary title starts with Modify", r.summary_title and r.summary_title.startswith("Modify")),
        ("Has rationale bullets", len(r.rationale_bullets) > 0),
        ("Has impact_accepted", r.impact_accepted is not None),
        ("Has impact_rejected", r.impact_rejected is not None),
    ]
    for desc, ok in checks:
        print(f"  {'✅' if ok else '❌'} {desc}")
        if ok: passed += 1
        total += 1

    # ── TEST 2: INSERT_NEW - Indemnification ──
    print("\n" + "=" * 60)
    print("TEST 2: INSERT_NEW - Indemnification (semantic placement)")
    print("=" * 60)
    total += 1
    r = service.locate(
        clause_type="indemnification",
        original_text="",
        proposed_text="10. Indemnification. Each party shall indemnify.",
        operation="insert",
    )
    checks = [
        ("Status resolved", r.status.value == "resolved"),
        ("Has section", r.section_id is not None),
        ("display_numbering false", r.display_numbering == False),
        ("Operation add_protection", r.clause_operation_type == "add_protection"),
        ("Action label ADD PROTECTION", r.action_label == "ADD PROTECTION"),
        ("Summary title", r.summary_title is not None),
        ("Has rationale bullets", len(r.rationale_bullets) > 0),
        ("Has impact_accepted", r.impact_accepted is not None),
        ("Has group_key", r.group_key is not None),
        ("Human reason (Suggested placement)", "Suggested placement" in (r.reason or "")),
    ]
    for desc, ok in checks:
        print(f"  {'✅' if ok else '❌'} {desc}")
        if ok: passed += 1
        total += 1

    # ── TEST 3: INSERT_NEW - Fee increase (within payment) ──
    print("\n" + "=" * 60)
    print("TEST 3: INSERT_NEW - Fee increase (within existing payment section)")
    print("=" * 60)
    total += 1
    r = service.locate(
        clause_type="fee_increase",
        original_text="",
        proposed_text="Fee increase cap. Fees shall not increase by more than 5%.",
        operation="insert",
    )
    checks = [
        ("Within section 2 (payment)", r.section_id == "2"),
        ("Insert position within_section", r.insert_position and r.insert_position.value == "within_section"),
        ("Summary title", r.summary_title is not None),
        ("Has rationale bullets", len(r.rationale_bullets) > 0),
        ("Has impact_accepted", r.impact_accepted is not None),
    ]
    for desc, ok in checks:
        print(f"  {'✅' if ok else '❌'} {desc}")
        if ok: passed += 1
        total += 1

    # ── TEST 4: INSERT_NEW - Confidentiality (standalone) ──
    print("\n" + "=" * 60)
    print("TEST 4: INSERT_NEW - Confidentiality (standalone, should not nest)")
    print("=" * 60)
    total += 1
    r = service.locate(
        clause_type="confidentiality",
        original_text="",
        proposed_text="Confidentiality. Each party shall maintain confidentiality.",
        operation="insert",
    )
    checks = [
        ("Has section", r.section_id is not None),
        ("Operation add_protection", r.clause_operation_type == "add_protection"),
        ("Has rationale bullets", len(r.rationale_bullets) > 0),
    ]
    for desc, ok in checks:
        print(f"  {'✅' if ok else '❌'} {desc}")
        if ok: passed += 1
        total += 1

    # ── TEST 5: Synthetic numbering stripping ──
    print("\n" + "=" * 60)
    print("TEST 5: Synthetic numbering stripping")
    print("=" * 60)
    strip_tests = [
        ("10. Indemnification. Each party shall indemnify.", "indemnification",
         "should start with [Suggested"),
        ("4.2 Work Product Ownership. Customer grants license.", "ip",
         "should start with [Suggested"),
        ("9.1.1 Notice Period. Either party may terminate.", "termination",
         "should start with [Suggested"),
        ("10. Limitation of Liability", "limitation_of_liability",
         "should start with [Suggested"),
        ("Normal text without numbering.", "test",
         "Normal text without numbering."),
    ]
    for text, ct, expected in strip_tests:
        total += 1
        result = _strip_synthetic_numbering(text, ct)
        if expected.startswith("should"):
            ok = result.startswith("[Suggested")
        else:
            ok = result == expected
        print(f"  {'✅' if ok else '❌'} {text[:40]:40s} -> {result[:50]}")
        if ok:
            passed += 1

    # ── TEST 6: Risk metadata completeness ──
    print("\n" + "=" * 60)
    print("TEST 6: Risk metadata completeness")
    print("=" * 60)
    for ct in ["indemnification", "payment", "termination", "renewal",
               "confidentiality", "data_privacy", "ip", "limitation_of_liability"]:
        total += 1
        data = CLAUSE_RISK_RELATIONSHIPS.get(ct, {})
        ok = bool(data.get("rationale_bullets")) and bool(data.get("impact_accepted"))
        print(f"  {'✅' if ok else '❌'} {ct}: bullets={len(data.get('rationale_bullets', []))} risks={data.get('related_risks', [])}")
        if ok:
            passed += 1

    # ── TEST 7: Clause intent mapping ──
    print("\n" + "=" * 60)
    print("TEST 7: Clause intent mapping")
    print("=" * 60)
    intent_tests = [
        ("fee_increase", "prevent_uncontrolled_cost_escalation"),
        ("auto_renewal", "prevent_automatic_silent_renewal"),
        ("indemnification", "allocate_risk_of_third_party_claims"),
    ]
    for ct, expected in intent_tests:
        total += 1
        actual = CLAUSE_INTENT.get(ct, "")
        ok = actual == expected
        print(f"  {'✅' if ok else '❌'} {ct}: {actual}")
        if ok:
            passed += 1

    # ── TEST 8: to_dict serialization ──
    print("\n" + "=" * 60)
    print("TEST 8: to_dict serialization")
    print("=" * 60)
    total += 1
    r = service.locate(
        clause_type="termination",
        original_text="",
        proposed_text="Termination. Either party may terminate.",
        operation="insert",
    )
    d = r.to_dict()
    required_keys = [
        "summary_title", "action_label", "group_key", "clause_operation_type",
        "rationale_bullets", "impact_accepted", "impact_rejected",
        "display_numbering", "legal_domain", "risk_type", "recommendation_type",
    ]
    missing = [k for k in required_keys if k not in d]
    ok = len(missing) == 0
    print(f"  {'✅' if ok else '❌'} All {len(required_keys)} required keys present. Missing: {missing or 'none'}")
    if ok:
        passed += 1
    total += 1

    # ── RESULTS ──
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    if passed == total:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {total - passed} TESTS FAILED")

    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
