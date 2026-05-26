"""
Comprehensive Test Script for ContractRiskEdge Platform
Tests all implemented use cases and exports results to Excel.
"""

import urllib.request
import json
import time
import sys
import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ── Configuration ────────────────────────────────────────────────────────────
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:3000")
API_URL = f"{BASE_URL}/api/v1"
REPORT_FILE = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

# Colors for Excel
PASS_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
FAIL_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
BOLD_FONT = Font(bold=True, size=11)
NORMAL_FONT = Font(size=10)
THIN_BORDER = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin')
)

# ── HTTP Helper ──────────────────────────────────────────────────────────────

class RedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = urllib.request.Request(newurl)
        new_req.headers.update(req.headers)
        return new_req

_opener = urllib.request.build_opener(RedirectHandler)


def api_request(method: str, path: str, token: str = "", body: dict = None, content_type: str = "application/json"):
    """Make an API request and return (success, status_code, data)."""
    url = f"{API_URL}{path}"
    
    # Handle redirects manually to preserve auth headers and body
    for redirect_count in range(5):
        req = urllib.request.Request(url, method=method)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        if content_type:
            req.add_header("Content-Type", content_type)
        if body is not None:
            data_bytes = json.dumps(body).encode()
        else:
            data_bytes = None
        try:
            r = _opener.open(req, data=data_bytes)
            status = r.status
            body_bytes = r.read()
            if body_bytes:
                resp_data = json.loads(body_bytes.decode())
            else:
                resp_data = {"status": "ok"}
            return True, status, resp_data
        except urllib.error.HTTPError as e:
            if e.code in (307, 308):
                # Follow redirect manually, preserving headers
                url = e.headers.get("Location", "")
                if url.startswith("/"):
                    url = f"{BASE_URL}{url}"
                method = "GET"  # browsers change POST to GET on redirect
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


# ── Test Cases ───────────────────────────────────────────────────────────────

def run_all_tests():
    """Run all test cases and return results list."""
    results = []
    token = get_token()
    print(f"✅ Auth token obtained (user: Admin)")

    def record(use_case: str, scenario: str, status: str, detail: str, duration: float = 0):
        results.append({
            "use_case": use_case,
            "scenario": scenario,
            "status": status,
            "detail": detail[:200],
            "duration_s": round(duration, 2),
        })
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"  {icon} {scenario}: {detail[:80]}")

    # ── 1. Authentication ────────────────────────────────────────────────
    print("\n📋 Use Case 1: Authentication")
    t0 = time.time()
    # 1a. Dev Login
    success, status, data = api_request("GET", "/auth/dev-login")
    record("Authentication", "Dev login returns token", "PASS" if success else "FAIL",
           f"HTTP {status}, token length={len(data.get('access_token',''))}", time.time() - t0)

    # 1b. Token Decode
    t0 = time.time()
    try:
        import base64
        parts = token.split(".")
        padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        has_manage_users = "manage:users" in payload.get("permissions", [])
        record("Authentication", "Token contains admin permissions", "PASS" if has_manage_users else "FAIL",
               f"User: {payload.get('name')}, Role: {payload.get('role')}, Perms: {len(payload.get('permissions',[]))}", time.time() - t0)
    except Exception as e:
        record("Authentication", "Token decode", "FAIL", str(e), time.time() - t0)

    # ── 2. User Management ───────────────────────────────────────────────
    print("\n📋 Use Case 2: User Management")
    t0 = time.time()
    success, status, data = api_request("GET", "/users", token)
    record("User Management", "List users", "PASS" if success else "FAIL",
           f"HTTP {status}, total={data.get('total',0)}", time.time() - t0)

    t0 = time.time()
    success, status, data = api_request("POST", "/users", token, {
        "user_id": "auth0|test_user",
        "email": "test@test.com",
        "name": "Test User",
        "role": "analyst"
    })
    record("User Management", "Create user", "PASS" if success else "FAIL",
           f"HTTP {status}", time.time() - t0)

    t0 = time.time()
    success, status, data = api_request("GET", "/users/auth0%7Ctest_user", token)
    record("User Management", "Get user by ID", "PASS" if success else "FAIL",
           f"HTTP {status}, name={data.get('name','')}", time.time() - t0)

    t0 = time.time()
    success, status, data = api_request("PATCH", "/users/auth0%7Ctest_user", token, {
        "name": "Updated User", "role": "admin"
    })
    record("User Management", "Update user", "PASS" if success else "FAIL",
           f"HTTP {status}, role={data.get('role','')}", time.time() - t0)

    t0 = time.time()
    success, status, _ = api_request("DELETE", "/users/auth0%7Ctest_user", token)
    record("User Management", "Delete user", "PASS" if success else "FAIL",
           f"HTTP {status}", time.time() - t0)

    # ── 3. Contracts ─────────────────────────────────────────────────────
    print("\n📋 Use Case 3: Contracts")
    t0 = time.time()
    success, status, data = api_request("GET", "/contracts", token)
    record("Contracts", "List contracts", "PASS" if success else "FAIL",
           f"HTTP {status}, total={data.get('total',0)}", time.time() - t0)

    if success and data.get("contracts"):
        c = data["contracts"][0]
        cid = c["contract_id"]
        record("Contracts", "Contract has valid fields", "PASS" if c.get("filename") else "FAIL",
               f"File: {c.get('filename')}, Type: {c.get('contract_type')}, Tags type: {type(c.get('tags')).__name__}", 0)

        t0 = time.time()
        s, st, d2 = api_request("GET", f"/contracts/{cid}", token)
        record("Contracts", "Get contract by ID", "PASS" if s else "FAIL",
               f"HTTP {st}, file={d2.get('filename','')}", time.time() - t0)

        t0 = time.time()
        s, st, d2 = api_request("POST", f"/contracts/search?query=Master", token)
        record("Contracts", "Search contracts", "PASS" if s else "FAIL",
               f"HTTP {st}, results={len(d2.get('results',[]))}", time.time() - t0)

    # ── 4. Risk Analysis ─────────────────────────────────────────────────
    print("\n📋 Use Case 4: Risk Analysis")
    t0 = time.time()
    cid = "c0000001-0000-0000-0000-000000000001"
    success, status, data = api_request("POST", f"/risks/analyze?contract_id={cid}&categories=indemnification&categories=liability_limitation", token, {})
    record("Risk Analysis", "Start risk analysis", "PASS" if success else "FAIL",
           f"HTTP {status}, report_id={data.get('report_id','')[:20]}", time.time() - t0)

    if success:
        report_id = data.get("report_id", "")
        # Poll for completion (up to 90s)
        for attempt in range(18):
            time.sleep(5)
            s, st, rd = api_request("GET", f"/risks/{report_id}", token)
            if rd.get("status") == "completed":
                summary = rd.get("results", {}).get("summary", {})
                record("Risk Analysis", "Analysis completed", "PASS",
                       f"Clauses: {summary.get('analyzed')}, Avg Severity: {summary.get('avg_severity')}, High: {summary.get('high_risk_count')}", (attempt + 1) * 5)
                break
            elif rd.get("status") == "failed":
                record("Risk Analysis", "Analysis failed", "FAIL",
                       rd.get("error", "Unknown error"), (attempt + 1) * 5)
                break
        else:
            record("Risk Analysis", "Analysis timeout", "FAIL",
                   "Did not complete within 90s", 90)

    # ── 5. Redline Suggestions ───────────────────────────────────────────
    print("\n📋 Use Case 5: Redline Suggestions")
    t0 = time.time()
    success, status, data = api_request("GET", "/redlines/suggest", token)
    record("Redlines", "List suggestions", "PASS" if success else "FAIL",
           f"HTTP {status}, total={data.get('total',0)}", time.time() - t0)

    t0 = time.time()
    success, status, data = api_request("POST", "/redlines/suggest", token, {
        "contract_id": cid,
        "clause_type": "indemnification",
        "original_clause_text": "The Supplier shall indemnify, defend, and hold harmless the Customer from and against any and all claims, damages, losses, liabilities, and expenses arising out of or related to any breach of this Agreement by the Supplier.",
        "party_role": "buyer",
        "deal_size_tier": "medium",
        "industry": "technology",
        "counterparty_aggressiveness": "moderate",
        "jurisdiction": "New York, USA"
    })
    record("Redlines", "Create suggestion", "PASS" if success else "FAIL",
           f"HTTP {status}, id={data.get('suggestion',{}).get('suggestion_id','')[:20]}", time.time() - t0)

    if success:
        sug_id = data["suggestion"]["suggestion_id"]
        t0 = time.time()
        s, st, d2 = api_request("GET", f"/redlines/suggest/{sug_id}", token)
        record("Redlines", "Get suggestion by ID", "PASS" if s else "FAIL",
               f"HTTP {st}, type={d2.get('clause_type','')}", time.time() - t0)

        t0 = time.time()
        s, st, _ = api_request("POST", f"/redlines/suggest/{sug_id}/accept", token)
        record("Redlines", "Accept suggestion", "PASS" if s else "FAIL",
               f"HTTP {st}", time.time() - t0)

        # Create another for reject test
        s2, st2, d3 = api_request("POST", "/redlines/suggest", token, {
            "contract_id": cid, "clause_type": "confidentiality",
            "original_clause_text": "The Receiving Party shall maintain strict confidentiality of all Confidential Information.",
            "party_role": "buyer", "deal_size_tier": "medium",
            "industry": "technology", "counterparty_aggressiveness": "moderate",
            "jurisdiction": "New York, USA"
        })
        if s2:
            sug_id2 = d3["suggestion"]["suggestion_id"]
            t0 = time.time()
            s3, st3, _ = api_request("POST", f"/redlines/suggest/{sug_id2}/reject", token)
            record("Redlines", "Reject suggestion", "PASS" if s3 else "FAIL",
                   f"HTTP {st3}", time.time() - t0)

    # ── 6. Health & Monitoring ───────────────────────────────────────────
    print("\n📋 Use Case 6: Health & Monitoring")
    t0 = time.time()
    success, status, data = api_request("GET", "/health")
    record("Monitoring", "Health check", "PASS" if success else "FAIL",
           f"HTTP {status}, status={data.get('status')}", time.time() - t0)

    t0 = time.time()
    success, status, data = api_request("GET", "/monitoring/health/detailed", token)
    record("Monitoring", "Detailed health", "PASS" if success else "FAIL",
           f"HTTP {status}, LLM={data.get('checks',{}).get('llm_providers',{}).get('status','?')}", time.time() - t0)

    # ── 7. Export ────────────────────────────────────────────────────────
    print("\n📋 Use Case 7: Export")
    t0 = time.time()
    try:
        url = f"{API_URL}/export/audit/csv"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        r = urllib.request.urlopen(req)
        csv_data = r.read().decode()
        record("Export", "Export audit CSV", "PASS" if len(csv_data) > 0 else "FAIL",
               f"HTTP {r.status}, size={len(csv_data)} bytes", time.time() - t0)
    except Exception as e:
        record("Export", "Export audit CSV", "FAIL", str(e)[:100], time.time() - t0)

    # ── 8. Evaluation ────────────────────────────────────────────────────
    print("\n📋 Use Case 8: Evaluation")
    t0 = time.time()
    success, status, data = api_request("GET", "/evaluation/metrics", token)
    record("Evaluation", "Get evaluation metrics", "PASS" if success else "FAIL",
           f"HTTP {status}", time.time() - t0)

    # ── 9. Playbooks ─────────────────────────────────────────────────────
    print("\n📋 Use Case 9: Playbooks")
    t0 = time.time()
    success, status, data = api_request("GET", "/playbooks", token)
    record("Playbooks", "List playbooks", "PASS" if success else "FAIL",
           f"HTTP {status}, total={len(data) if isinstance(data,list) else data.get('total',0)}", time.time() - t0)

    return results


# ── Excel Export ──────────────────────────────────────────────────────────────

def export_to_excel(results: list):
    """Export test results to a formatted Excel file."""
    wb = Workbook()
    
    # ── Summary Sheet ──
    ws_summary = wb.active
    ws_summary.title = "Summary"
    ws_summary.merge_cells("A1:F1")
    ws_summary["A1"] = "ContractRiskEdge - Test Report"
    ws_summary["A1"].font = Font(bold=True, size=16, color="1E3A5F")
    ws_summary["A1"].alignment = Alignment(horizontal="center")

    ws_summary["A3"] = "Generated:"
    ws_summary["B3"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws_summary["A4"] = "Environment:"
    ws_summary["B4"] = BASE_URL
    ws_summary["A5"] = "Total Tests:"
    ws_summary["B5"] = len(results)
    ws_summary["A6"] = "Passed:"
    passed = sum(1 for r in results if r["status"] == "PASS")
    ws_summary["B6"] = passed
    ws_summary["B6"].font = Font(bold=True, color="006100")
    ws_summary["A7"] = "Failed:"
    failed = sum(1 for r in results if r["status"] == "FAIL")
    ws_summary["B7"] = failed
    ws_summary["B7"].font = Font(bold=True, color="9C0006")
    ws_summary["A8"] = "Pass Rate:"
    ws_summary["B8"] = f"{passed / len(results) * 100:.1f}%" if results else "N/A"

    # ── Use Case Summary ──
    ws_summary["A10"] = "Use Case Summary"
    ws_summary["A10"].font = BOLD_FONT
    headers_usc = ["Use Case", "Total", "Passed", "Failed", "Pass Rate"]
    for i, h in enumerate(headers_usc, 1):
        cell = ws_summary.cell(row=11, column=i, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
        cell.alignment = Alignment(horizontal="center")

    use_cases = {}
    for r in results:
        use_cases.setdefault(r["use_case"], {"total": 0, "passed": 0, "failed": 0})
        use_cases[r["use_case"]]["total"] += 1
        if r["status"] == "PASS":
            use_cases[r["use_case"]]["passed"] += 1
        else:
            use_cases[r["use_case"]]["failed"] += 1

    for row_idx, (uc, stats) in enumerate(sorted(use_cases.items()), 12):
        ws_summary.cell(row=row_idx, column=1, value=uc).border = THIN_BORDER
        ws_summary.cell(row=row_idx, column=2, value=stats["total"]).border = THIN_BORDER
        ws_summary.cell(row=row_idx, column=3, value=stats["passed"]).border = THIN_BORDER
        ws_summary.cell(row=row_idx, column=4, value=stats["failed"]).border = THIN_BORDER
        rate = f"{stats['passed'] / stats['total'] * 100:.0f}%" if stats["total"] else "N/A"
        cell = ws_summary.cell(row=row_idx, column=5, value=rate)
        cell.border = THIN_BORDER
        if stats["failed"] == 0:
            cell.fill = PASS_FILL
        else:
            cell.fill = FAIL_FILL

    ws_summary.column_dimensions["A"].width = 20
    ws_summary.column_dimensions["B"].width = 30
    ws_summary.column_dimensions["C"].width = 12
    ws_summary.column_dimensions["D"].width = 12
    ws_summary.column_dimensions["E"].width = 12

    # ── Details Sheet ──
    ws_details = wb.create_sheet("Test Details")
    headers = ["#", "Use Case", "Scenario", "Status", "Detail", "Duration (s)"]
    for i, h in enumerate(headers, 1):
        cell = ws_details.cell(row=1, column=i, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
        cell.alignment = Alignment(horizontal="center")

    for row_idx, r in enumerate(results, 2):
        ws_details.cell(row=row_idx, column=1, value=row_idx - 1).border = THIN_BORDER
        ws_details.cell(row=row_idx, column=2, value=r["use_case"]).border = THIN_BORDER
        ws_details.cell(row=row_idx, column=3, value=r["scenario"]).border = THIN_BORDER
        status_cell = ws_details.cell(row=row_idx, column=4, value=r["status"])
        status_cell.border = THIN_BORDER
        status_cell.fill = PASS_FILL if r["status"] == "PASS" else FAIL_FILL
        ws_details.cell(row=row_idx, column=5, value=r["detail"]).border = THIN_BORDER
        ws_details.cell(row=row_idx, column=6, value=r["duration_s"]).border = THIN_BORDER
        ws_details.cell(row=row_idx, column=6).number_format = "0.00"

    ws_details.column_dimensions["A"].width = 5
    ws_details.column_dimensions["B"].width = 20
    ws_details.column_dimensions["C"].width = 30
    ws_details.column_dimensions["D"].width = 10
    ws_details.column_dimensions["E"].width = 60
    ws_details.column_dimensions["F"].width = 12

    wb.save(REPORT_FILE)
    return REPORT_FILE


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  ContractRiskEdge - Comprehensive Test Suite")
    print(f"  Target: {API_URL}")
    print("=" * 60)

    results = run_all_tests()

    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    print(f"  Results: {passed} passed, {failed} failed, {len(results)} total")
    print(f"  Pass Rate: {passed / len(results) * 100:.1f}%")

    filepath = export_to_excel(results)
    print(f"\n📊 Report exported: {filepath}")
    print("=" * 60)
