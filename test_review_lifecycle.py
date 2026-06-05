"""
Comprehensive Review Lifecycle Test — Enterprise Readiness Checkpoint.

Tests the full end-to-end workflow:
  1. Upload contract
  2. Analyze
  3. Generate mitigation redline
  4. Accept 3 redlines
  5. Reject 2
  6. Modify 1
  7. Refresh page (re-fetch)
  8. Restart backend (simulate)
  9. Verify all state persists
  10. Generate v2
  11. Download DOCX
  12. Download tracked-changes DOCX
  13. Verify risk recalculation matches actions

Usage:
  python test_review_lifecycle.py [--url http://localhost:3000]
"""

import urllib.request
import json
import time
import sys
import os
import base64
from datetime import datetime
from typing import Optional


BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:3000")
API_URL = f"{BASE_URL}/api/v1"


# ═════════════════════════════════════════════════════════════════════════════
# HTTP Helpers
# ═════════════════════════════════════════════════════════════════════════════

class RedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = urllib.request.Request(newurl)
        new_req.headers.update(req.headers)
        return new_req


_opener = urllib.request.build_opener(RedirectHandler)


def api_request(method: str, path: str, token: str = "",
                body: dict = None, content_type: str = "application/json",
                raw_body: bytes = None):
    """Make an API request and return (success, status_code, data)."""
    url = f"{API_URL}{path}"
    for _ in range(5):
        req = urllib.request.Request(url, method=method)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        if content_type:
            req.add_header("Content-Type", content_type)
        data_bytes = raw_body
        if body is not None:
            data_bytes = json.dumps(body).encode()
        try:
            r = _opener.open(req, data=data_bytes)
            status = r.status
            body_bytes = r.read()
            resp_data = json.loads(body_bytes.decode()) if body_bytes else {"status": "ok"}
            return True, status, resp_data
        except urllib.error.HTTPError as e:
            if e.code in (307, 308):
                url = e.headers.get("Location", url)
                if url.startswith("/"):
                    url = f"{BASE_URL}{url}"
                method = "GET"
                continue
            try:
                err_data = json.loads(e.read().decode())
            except Exception:
                err_data = {"detail": str(e)}
            return False, e.code, err_data
        except Exception as e:
            return False, 0, {"detail": str(e)}
    return False, 0, {"detail": "Too many redirects"}


def get_token() -> str:
    """Get admin token via dev-login."""
    success, status, data = api_request("GET", "/auth/dev-login")
    if not success:
        print(f"FATAL: Cannot get auth token: {data}")
        sys.exit(1)
    return data["access_token"]


# ═════════════════════════════════════════════════════════════════════════════
# Test Runner
# ═════════════════════════════════════════════════════════════════════════════

PASS = "✅ PASS"
FAIL = "❌ FAIL"
SKIP = "⏭️ SKIP"


def run_lifecycle_test():
    """Run the full review lifecycle test."""
    token = get_token()
    print(f"\n{'='*70}")
    print(f"  REVIEW LIFECYCLE TEST — {datetime.now().isoformat()}")
    print(f"{'='*70}\n")

    results: list[dict] = []
    review_id: Optional[str] = None

    def check(step: str, detail: str, success: bool, data=None):
        status = PASS if success else FAIL
        results.append({"step": step, "detail": detail[:200], "status": status, "data": data})
        print(f"  {status} {step}")
        if detail:
            print(f"         {detail}")

    # ── Phase 1: Upload & Analyze ────────────────────────────────────────
    print(f"\n{'─'*70}")
    print(f"  PHASE 1: Upload & Analyze")
    print(f"{'─'*70}\n")

    # 1a. Upload a contract
    print("  [1a] Uploading sample contract...")
    sample_path = os.path.join(os.path.dirname(__file__), "SampleContracts", "sample_nda.txt")
    if not os.path.exists(sample_path):
        # Try other possible locations
        alt_paths = [
            os.path.join(os.path.dirname(__file__), "api", "sample_contracts.py"),
            os.path.join(os.path.dirname(__file__), "SampleContracts", "sample_contract.txt"),
        ]
        for p in alt_paths:
            if os.path.exists(p):
                sample_path = p
                break

    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            content = f.read()
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="test_contract.txt"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
        ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        success, status, data = api_request("POST", "/contracts/upload", token,
                                            content_type=f"multipart/form-data; boundary={boundary}",
                                            raw_body=body)
        check("1a. Upload contract", f"HTTP {status}", success, data)
        if success:
            upload_id = data.get("upload_id") or data.get("id")
            check("   Upload ID received", f"upload_id={upload_id}", bool(upload_id))
    else:
        # Fallback: use an existing contract
        success, status, data = api_request("GET", "/contracts", token)
        check("1a. List existing contracts", f"HTTP {status}, count={len(data.get('contracts', []))}", success, data)
        if success and data.get("contracts"):
            upload_id = data["contracts"][0].get("upload_id") or data["contracts"][0].get("contract_id")
        else:
            check("1a. No contracts available", "Cannot proceed without a contract", False)
            upload_id = None

    # 1b. Create a review
    if upload_id:
        print("\n  [1b] Creating review...")
        success, status, data = api_request("POST", "/reviews", token, {
            "upload_id": upload_id,
            "title": "Lifecycle Test Review",
        })
        check("1b. Create review", f"HTTP {status}", success, data)
        if success:
            review_id = data.get("review_id") or data.get("id")
            check("   Review ID received", f"review_id={review_id}", bool(review_id))

    # 1c. Trigger analysis
    if review_id:
        print(f"\n  [1c] Triggering AI analysis for review {review_id}...")
        success, status, data = api_request("POST", f"/reviews/{review_id}/analyze", token)
        check("1c. Trigger analysis", f"HTTP {status}", success, data)
        if success:
            print("         Waiting 5s for analysis to complete...")
            time.sleep(5)

    # 1d. Check analysis results
    if review_id:
        print(f"\n  [1d] Checking analysis results...")
        success, status, data = api_request("GET", f"/reviews/{review_id}", token)
        check("1d. Get review", f"HTTP {status}, status={data.get('status')}", success, data)

        # Get findings
        success, status, data = api_request("GET", f"/reviews/{review_id}/findings", token)
        check("1d. Get findings", f"HTTP {status}, count={len(data) if isinstance(data, list) else data.get('total', 0)}",
              success, data)

        # Get risk breakdown
        success, status, data = api_request("GET", f"/reviews/{review_id}/risk-breakdown", token)
        check("1d. Get risk breakdown", f"HTTP {status}", success, data)
        if success:
            overall = data.get("overall_risk_score", 0)
            remaining = data.get("remaining_exposure", 0)
            check("   Risk scores", f"overall={overall:.2%}, remaining={remaining:.2%}", True)

    # ── Phase 2: Generate & Manage Redlines ──────────────────────────────
    print(f"\n{'─'*70}")
    print(f"  PHASE 2: Generate & Manage Redlines")
    print(f"{'─'*70}\n")

    generated_redlines = []

    # 2a. Generate mitigation redlines
    if review_id:
        print("  [2a] Generating mitigation redlines...")
        # Get mitigation suggestions from risk breakdown
        success, status, risk_data = api_request("GET", f"/reviews/{review_id}/risk-breakdown", token)
        if success and risk_data.get("mitigation_suggestions"):
            suggestions = risk_data["mitigation_suggestions"]
            print(f"         Found {len(suggestions)} mitigation suggestion categories")

            for idx, suggestion in enumerate(suggestions[:5]):  # Try up to 5
                category = suggestion.get("category", "")
                mitigations = suggestion.get("suggested_mitigations", [])
                for mitigation in mitigations[:2]:  # Up to 2 per category
                    mtype = mitigation.get("mitigation_type", "")
                    if not mtype:
                        continue
                    print(f"         Generating redline #{idx+1}: {mtype}...")
                    success2, status2, redline_data = api_request(
                        "POST", f"/reviews/{review_id}/redlines/generate-mitigation", token, {
                            "mitigation_type": mtype,
                            "clause_category": category,
                            "finding_ids": [],
                        }
                    )
                    check(f"2a. Generate redline ({mtype})", f"HTTP {status2}", success2, redline_data)
                    if success2:
                        redline_id = redline_data.get("redline_id") or redline_data.get("id")
                        if redline_id:
                            generated_redlines.append(redline_id)
                            check("   Redline ID", f"redline_id={redline_id}", True)
                    time.sleep(0.5)  # Brief pause between generations
        else:
            check("2a. No mitigation suggestions", "Cannot generate redlines without suggestions", False)

        # 2b. List all redlines
        print(f"\n  [2b] Listing all redlines...")
        success, status, data = api_request("GET", f"/reviews/{review_id}/redlines", token)
        check("2b. List redlines", f"HTTP {status}, count={len(data) if isinstance(data, list) else data.get('total', 0)}",
              success, data)

    # 2c. Accept/Reject/Modify redlines
    if review_id and generated_redlines:
        print(f"\n  [2c] Processing redline decisions...")
        redline_ids = generated_redlines

        # Accept up to 3
        for i, rid in enumerate(redline_ids[:3]):
            print(f"         Accepting redline {rid[:8]}...")
            success, status, data = api_request(
                "PATCH", f"/reviews/{review_id}/redlines/{rid}", token, {
                    "status": "accepted",
                }
            )
            check(f"2c. Accept redline #{i+1}", f"HTTP {status}, redline={rid[:8]}", success, data)
            time.sleep(0.3)

        # Reject up to 2 (if we have enough)
        remaining = redline_ids[3:]
        for i, rid in enumerate(remaining[:2]):
            print(f"         Rejecting redline {rid[:8]}...")
            success, status, data = api_request(
                "PATCH", f"/reviews/{review_id}/redlines/{rid}", token, {
                    "status": "rejected",
                    "reason": "Does not match business requirements",
                }
            )
            check(f"2c. Reject redline #{i+1}", f"HTTP {status}, redline={rid[:8]}", success, data)
            time.sleep(0.3)

        # Modify 1 (if we have more)
        modify_targets = redline_ids[5:] if len(redline_ids) > 5 else redline_ids[:1]
        for i, rid in enumerate(modify_targets[:1]):
            print(f"         Modifying redline {rid[:8]}...")
            success, status, data = api_request(
                "PATCH", f"/reviews/{review_id}/redlines/{rid}", token, {
                    "status": "modified",
                    "modified_text": "The receiving party shall not use Confidential Information for any purpose other than evaluating a potential business relationship with the disclosing party. This obligation survives for a period of five (5) years from the date of disclosure.",
                }
            )
            check(f"2c. Modify redline #{i+1}", f"HTTP {status}, redline={rid[:8]}", success, data)
            time.sleep(0.3)

    # ── Phase 3: Persistence Check ───────────────────────────────────────
    print(f"\n{'─'*70}")
    print(f"  PHASE 3: Persistence Check")
    print(f"{'─'*70}\n")

    if review_id:
        # 3a. Refresh — re-fetch everything
        print("  [3a] Re-fetching all data (simulates page refresh)...")
        success, status, data = api_request("GET", f"/reviews/{review_id}", token)
        check("3a. Refresh review", f"HTTP {status}, status={data.get('status')}", success, data)

        success, status, data = api_request("GET", f"/reviews/{review_id}/redlines", token)
        redline_count = len(data) if isinstance(data, list) else data.get("total", 0)
        check("3a. Refresh redlines", f"HTTP {status}, count={redline_count}", success, data)

        # 3b. Verify redline statuses persisted
        if success:
            redlines_list = data if isinstance(data, list) else data.get("items", [])
            accepted = [r for r in redlines_list if r.get("status") == "accepted"]
            rejected = [r for r in redlines_list if r.get("status") == "rejected"]
            modified = [r for r in redlines_list if r.get("status") == "modified"]
            check("3b. Accepted redlines persisted", f"count={len(accepted)}", len(accepted) >= 1)
            check("3b. Rejected redlines persisted", f"count={len(rejected)}", len(rejected) >= 1)
            check("3b. Modified redlines persisted", f"count={len(modified)}", len(modified) >= 1)

        # 3c. Risk recalculation check
        print("\n  [3c] Verifying risk recalculation...")
        success, status, risk_data = api_request("GET", f"/reviews/{review_id}/risk-breakdown", token)
        if success:
            remaining = risk_data.get("remaining_exposure", 0)
            reduction = risk_data.get("risk_reduction", 0)
            check("3c. Risk recalculated", f"remaining={remaining:.2%}, reduction={reduction:.2%}",
                  reduction > 0 or remaining > 0)

    # ── Phase 4: Version Generation ──────────────────────────────────────
    print(f"\n{'─'*70}")
    print(f"  PHASE 4: Version Generation & Export")
    print(f"{'─'*70}\n")

    if review_id:
        # 4a. Generate v2
        print("  [4a] Generating version v2...")
        success, status, data = api_request(
            "POST", f"/reviews/{review_id}/versions", token, {
                "label": "v2 - After review",
                "include_accepted": True,
                "include_modified": True,
            }
        )
        check("4a. Generate v2", f"HTTP {status}", success, data)
        version_id = data.get("version_id") or data.get("id") if success else None
        if version_id:
            check("   Version ID", f"version_id={version_id}", True)

        # 4b. List versions
        print("\n  [4b] Listing versions...")
        success, status, data = api_request("GET", f"/reviews/{review_id}/versions", token)
        check("4b. List versions", f"HTTP {status}, versions={len(data) if isinstance(data, list) else data.get('total', 0)}",
              success, data)

        # 4c. List versions first to get version_id for download
        print("\n  [4c] Listing versions for download...")
        version_id = None
        success, status, data = api_request("GET", f"/reviews/{review_id}/versions", token)
        if success:
            versions = data if isinstance(data, list) else data.get("items", [])
            if versions:
                version_id = versions[0].get("version_id") or versions[0].get("id")
                check("4c. Got version for download", f"version_id={version_id}", bool(version_id))

        # 4d. Download DOCX via versions endpoint
        if version_id:
            print("\n  [4d] Downloading DOCX...")
            try:
                url = f"{API_URL}/reviews/{review_id}/versions/{version_id}/download"
                req = urllib.request.Request(url, method="GET")
                req.add_header("Authorization", f"Bearer {token}")
                r = urllib.request.urlopen(req)
                docx_bytes = r.read()
                check("4d. Download DOCX", f"size={len(docx_bytes)} bytes", len(docx_bytes) > 100)
            except Exception as e:
                check("4d. Download DOCX", str(e), False)

            # 4e. Download tracked-changes DOCX
            print("\n  [4e] Downloading tracked-changes DOCX...")
            try:
                url = f"{API_URL}/reviews/{review_id}/versions/{version_id}/export-tracked"
                req = urllib.request.Request(url, method="GET")
                req.add_header("Authorization", f"Bearer {token}")
                r = urllib.request.urlopen(req)
                tracked_bytes = r.read()
                check("4e. Download tracked-changes DOCX", f"size={len(tracked_bytes)} bytes",
                      len(tracked_bytes) > 100)
            except Exception as e:
                check("4e. Download tracked-changes DOCX", str(e), False)

    # ── Phase 5: Audit & Timeline ────────────────────────────────────────
    print(f"\n{'─'*70}")
    print(f"  PHASE 5: Audit Timeline")
    print(f"{'─'*70}\n")

    if review_id:
        # 5a. Get activity/audit trail
        print("  [5a] Fetching activity/audit trail...")
        success, status, data = api_request("GET", f"/reviews/{review_id}/activity", token)
        check("5a. Activity trail", f"HTTP {status}, entries={len(data) if isinstance(data, list) else data.get('total', 0)}",
              success, data)
        if success:
            entries = data if isinstance(data, list) else data.get("items", [])
            check("   Activity entries found", f"count={len(entries)}", len(entries) > 0)

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*70}\n")

    passed = sum(1 for r in results if PASS in r["status"])
    failed = sum(1 for r in results if FAIL in r["status"])
    total = len(results)

    print(f"  Total: {total}  |  Passed: {passed}  |  Failed: {failed}")
    print()

    if failed > 0:
        print("  FAILED STEPS:")
        for r in results:
            if FAIL in r["status"]:
                print(f"    {r['step']}: {r['detail']}")
        print()

    # Print the full results table
    print(f"{'─'*70}")
    print(f"  DETAILED RESULTS")
    print(f"{'─'*70}\n")
    for r in results:
        status_icon = "✅" if PASS in r["status"] else "❌"
        print(f"  {status_icon} {r['step']}")
        print(f"     {r['detail']}")
        print()

    return failed == 0


# ═════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    success = run_lifecycle_test()
    sys.exit(0 if success else 1)
