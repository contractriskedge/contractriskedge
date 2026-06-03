"""Email notification templates — HTML templates for all 8 notification types.

Each template function returns an HTML string with inline styles
(for email client compatibility).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def _base_html(content: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f5f7;padding:32px 16px">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08)">
<tr><td style="padding:32px 32px 16px;background:linear-gradient(135deg,#1e293b 0%,#334155 100%)">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td><h1 style="margin:0;font-size:20px;font-weight:700;color:#ffffff;letter-spacing:-0.3px">Contract Risk Edge</h1></td></tr>
<tr><td><p style="margin:4px 0 0;font-size:13px;color:#94a3b8">Contract Review Platform</p></td></tr>
</table>
</td></tr>
<tr><td style="padding:32px 32px 24px">
{content}
</td></tr>
<tr><td style="padding:16px 32px;background-color:#f8fafc;border-top:1px solid #e2e8f0">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td><p style="margin:0;font-size:12px;color:#94a3b8">© {datetime.utcnow().year} Contract Risk Edge. All rights reserved.</p></td></tr>
<tr><td><p style="margin:4px 0 0;font-size:11px;color:#cbd5e1">This is an automated notification from the Contract Risk Edge platform.</p></td></tr>
</table>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _button_html(url: str, text: str) -> str:
    return f"""<table cellpadding="0" cellspacing="0" style="margin:20px 0">
<tr><td align="center" style="background-color:#1e293b;border-radius:6px;padding:0">
<a href="{url}" target="_blank" style="display:inline-block;padding:12px 28px;font-size:14px;font-weight:600;color:#ffffff;text-decoration:none;background-color:#1e293b;border-radius:6px">{text}</a>
</td></tr>
</table>"""


def _contract_info(contract_name: str, review_id: str, status: Optional[str] = None,
                    risk_score: Optional[float] = None, priority: Optional[str] = None,
                    reviewer: Optional[str] = None, current_stage: Optional[str] = None,
                    due_date: Optional[str] = None) -> str:
    priority_color = "#dc2626" if priority and priority in ("CRITICAL", "HIGH") else "#d97706" if priority == "MEDIUM" else "#16a34a"
    risk_color = "#dc2626" if risk_score and risk_score >= 7 else "#d97706" if risk_score and risk_score >= 4 else "#16a34a"

    html = f"""<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;border-radius:6px;padding:16px;margin:16px 0">
<tr><td style="font-size:13px;color:#475569;padding-bottom:4px"><strong>Contract:</strong> {contract_name}</td></tr>
<tr><td style="font-size:13px;color:#475569;padding-bottom:4px"><strong>Review ID:</strong> {review_id[:12] if review_id else "—"}...</td></tr>"""
    if status:
        html += f"""<tr><td style="font-size:13px;color:#475569;padding-bottom:4px"><strong>Status:</strong> {status}</td></tr>"""
    if current_stage:
        html += f"""<tr><td style="font-size:13px;color:#475569;padding-bottom:4px"><strong>Stage:</strong> {current_stage.replace('_', ' ').title()}</td></tr>"""
    if risk_score is not None:
        html += f"""<tr><td style="font-size:13px;padding-bottom:4px"><strong>Risk Score:</strong> <span style="color:{risk_color};font-weight:700">{risk_score}/10</span></td></tr>"""
    if priority:
        html += f"""<tr><td style="font-size:13px;padding-bottom:4px"><strong>Priority:</strong> <span style="color:{priority_color};font-weight:700">{priority}</span></td></tr>"""
    if reviewer:
        html += f"""<tr><td style="font-size:13px;color:#475569;padding-bottom:4px"><strong>Reviewer:</strong> {reviewer}</td></tr>"""
    if due_date:
        try:
            from datetime import datetime
            dd = datetime.fromisoformat(due_date.replace('Z', '+00:00')).strftime("%b %d, %Y %I:%M %p")
            html += f"""<tr><td style="font-size:13px;color:#475569;padding-bottom:4px"><strong>Due:</strong> {dd}</td></tr>"""
        except (ValueError, TypeError):
            html += f"""<tr><td style="font-size:13px;color:#475569;padding-bottom:4px"><strong>Due:</strong> {due_date}</td></tr>"""
    html += """</table>"""
    return html


def render_review_assigned(recipient_name: str, contract_name: str, review_id: str,
                            assigned_by: str = "System", due_date: Optional[str] = None,
                            app_url: str = "http://localhost:3000",
                            risk_score: Optional[float] = None, priority: Optional[str] = None,
                            reviewer: Optional[str] = None, current_stage: Optional[str] = None,
                            **kwargs) -> str:
    content = f"""<h2 style="margin:0 0 4px;font-size:18px;font-weight:700;color:#1e293b">Review Assigned</h2>
<p style="margin:0 0 16px;font-size:14px;color:#64748b">You have been assigned a contract review.</p>
<p style="font-size:14px;color:#334155">Hello {recipient_name},</p>
<p style="font-size:14px;color:#334155;line-height:1.6">A contract review has been assigned to you by <strong>{assigned_by}</strong>. Please review the contract at your earliest convenience.</p>
{_contract_info(contract_name, review_id, "Assigned", risk_score, priority, reviewer, current_stage, due_date)}
{_button_html(f"{app_url}/reviews/ai-workspace?reviewId={review_id}", "Open Review")}"""
    return _base_html(content)


def render_legal_approval_required(recipient_name: str, contract_name: str, review_id: str,
                                    requested_by: str = "System", app_url: str = "http://localhost:3000",
                                    risk_score: Optional[float] = None, priority: Optional[str] = None,
                                    reviewer: Optional[str] = None, current_stage: Optional[str] = None,
                                    due_date: Optional[str] = None, **kwargs) -> str:
    content = f"""<h2 style="margin:0 0 4px;font-size:18px;font-weight:700;color:#1e293b">Legal Approval Required</h2>
<p style="margin:0 0 16px;font-size:14px;color:#64748b">A contract requires your legal review and approval.</p>
<p style="font-size:14px;color:#334155">Hello {recipient_name},</p>
<p style="font-size:14px;color:#334155;line-height:1.6">Legal approval has been requested by <strong>{requested_by}</strong> for the following contract. Please review the findings and provide your decision.</p>
{_contract_info(contract_name, review_id, "Pending Legal Approval", risk_score, priority, reviewer, current_stage, due_date)}
{_button_html(f"{app_url}/reviews/ai-workspace?reviewId={review_id}", "Review & Approve")}"""
    return _base_html(content)


def render_executive_approval_required(recipient_name: str, contract_name: str, review_id: str,
                                        requested_by: str = "System", app_url: str = "http://localhost:3000",
                                        risk_score: Optional[float] = None, priority: Optional[str] = None,
                                        reviewer: Optional[str] = None, current_stage: Optional[str] = None,
                                        due_date: Optional[str] = None, **kwargs) -> str:
    content = f"""<h2 style="margin:0 0 4px;font-size:18px;font-weight:700;color:#1e293b">Executive Approval Required</h2>
<p style="margin:0 0 16px;font-size:14px;color:#64748b">Executive sign-off is needed for this contract.</p>
<p style="font-size:14px;color:#334155">Hello {recipient_name},</p>
<p style="font-size:14px;color:#334155;line-height:1.6">Executive approval has been requested by <strong>{requested_by}</strong>. This contract has completed legal review and now requires your final authorization.</p>
{_contract_info(contract_name, review_id, "Pending Executive Approval", risk_score, priority, reviewer, current_stage, due_date)}
{_button_html(f"{app_url}/reviews/ai-workspace?reviewId={review_id}", "Review & Approve")}"""
    return _base_html(content)


def render_escalated_review(recipient_name: str, contract_name: str, review_id: str,
                             escalated_by: str = "System", reason: str = "No reason provided",
                             app_url: str = "http://localhost:3000",
                             risk_score: Optional[float] = None, priority: Optional[str] = None,
                             reviewer: Optional[str] = None, current_stage: Optional[str] = None,
                             due_date: Optional[str] = None, **kwargs) -> str:
    content = f"""<h2 style="margin:0 0 4px;font-size:18px;font-weight:700;color:#dc2626">Review Escalated</h2>
<p style="margin:0 0 16px;font-size:14px;color:#64748b">A contract review has been escalated for attention.</p>
<p style="font-size:14px;color:#334155">Hello {recipient_name},</p>
<p style="font-size:14px;color:#334155;line-height:1.6">This review was escalated by <strong>{escalated_by}</strong> with the following reason:</p>
<blockquote style="margin:12px 0;padding:12px 16px;background-color:#fef2f2;border-left:4px solid #dc2626;border-radius:4px;font-size:13px;color:#991b1b">{reason}</blockquote>
{_contract_info(contract_name, review_id, "Escalated", risk_score, priority, reviewer, current_stage, due_date)}
{_button_html(f"{app_url}/reviews/ai-workspace?reviewId={review_id}", "View Escalated Review")}"""
    return _base_html(content)


def render_rejected_review(recipient_name: str, contract_name: str, review_id: str,
                            rejected_by: str = "System", reason: Optional[str] = None,
                            app_url: str = "http://localhost:3000",
                            risk_score: Optional[float] = None, priority: Optional[str] = None,
                            reviewer: Optional[str] = None, current_stage: Optional[str] = None,
                            due_date: Optional[str] = None, **kwargs) -> str:
    content = f"""<h2 style="margin:0 0 4px;font-size:18px;font-weight:700;color:#dc2626">Review Rejected</h2>
<p style="margin:0 0 16px;font-size:14px;color:#64748b">A contract review has been rejected.</p>
<p style="font-size:14px;color:#334155">Hello {recipient_name},</p>
<p style="font-size:14px;color:#334155;line-height:1.6">The review for the following contract was rejected by <strong>{rejected_by}</strong>.</p>
{f'<blockquote style="margin:12px 0;padding:12px 16px;background-color:#fef2f2;border-left:4px solid #dc2626;border-radius:4px;font-size:13px;color:#991b1b">{reason}</blockquote>' if reason else ''}
{_contract_info(contract_name, review_id, "Rejected", risk_score, priority, reviewer, current_stage, due_date)}
{_button_html(f"{app_url}/reviews/ai-workspace?reviewId={review_id}", "View Details")}"""
    return _base_html(content)


def render_sla_warning(recipient_name: str, contract_name: str, review_id: str,
                        remaining_hours: int = 24, assignee: Optional[str] = None,
                        app_url: str = "http://localhost:3000",
                        risk_score: Optional[float] = None, priority: Optional[str] = None,
                        reviewer: Optional[str] = None, current_stage: Optional[str] = None,
                        due_date: Optional[str] = None, **kwargs) -> str:
    urgency = "high" if remaining_hours < 4 else "medium"
    color = "#dc2626" if remaining_hours < 4 else "#d97706"
    content = f"""<h2 style="margin:0 0 4px;font-size:18px;font-weight:700;color:{color}">SLA Deadline Warning</h2>
<p style="margin:0 0 16px;font-size:14px;color:#64748b">A contract review is approaching its SLA deadline.</p>
<p style="font-size:14px;color:#334155">Hello {recipient_name},</p>
<p style="font-size:14px;color:#334155;line-height:1.6">The following review has <strong style="color:{color}">{remaining_hours} hour{'s' if remaining_hours != 1 else ''} remaining</strong> before its SLA deadline{f' (assigned to {assignee})' if assignee else ''}.</p>
{_contract_info(contract_name, review_id, f"SLA: {remaining_hours}h remaining", risk_score, priority, reviewer, current_stage, due_date)}
{_button_html(f"{app_url}/reviews/ai-workspace?reviewId={review_id}", "View Review")}"""
    return _base_html(content)


def render_review_approved(recipient_name: str, contract_name: str, review_id: str,
                            approved_by: str = "System", app_url: str = "http://localhost:3000",
                            risk_score: Optional[float] = None, priority: Optional[str] = None,
                            reviewer: Optional[str] = None, current_stage: Optional[str] = None,
                            due_date: Optional[str] = None, **kwargs) -> str:
    content = f"""<h2 style="margin:0 0 4px;font-size:18px;font-weight:700;color:#16a34a">Review Approved</h2>
<p style="margin:0 0 16px;font-size:14px;color:#64748b">A contract review has been approved.</p>
<p style="font-size:14px;color:#334155">Hello {recipient_name},</p>
<p style="font-size:14px;color:#334155;line-height:1.6">The review for the following contract was approved by <strong>{approved_by}</strong>. The contract can now proceed to finalization.</p>
{_contract_info(contract_name, review_id, "Approved", risk_score, priority, reviewer, current_stage, due_date)}
{_button_html(f"{app_url}/reviews/ai-workspace?reviewId={review_id}", "View Approved Review")}"""
    return _base_html(content)


def render_review_closed(recipient_name: str, contract_name: str, review_id: str,
                          closed_by: str = "System", app_url: str = "http://localhost:3000",
                          risk_score: Optional[float] = None, priority: Optional[str] = None,
                          reviewer: Optional[str] = None, current_stage: Optional[str] = None,
                          due_date: Optional[str] = None, **kwargs) -> str:
    content = f"""<h2 style="margin:0 0 4px;font-size:18px;font-weight:700;color:#64748b">Review Closed</h2>
<p style="margin:0 0 16px;font-size:14px;color:#64748b">A contract review has been closed.</p>
<p style="font-size:14px;color:#334155">Hello {recipient_name},</p>
<p style="font-size:14px;color:#334155;line-height:1.6">The review for the following contract was closed by <strong>{closed_by}</strong>. The contract lifecycle is now complete.</p>
{_contract_info(contract_name, review_id, "Closed", risk_score, priority, reviewer, current_stage, due_date)}
{_button_html(f"{app_url}/reviews/ai-workspace?reviewId={review_id}", "View Closed Review")}"""
    return _base_html(content)


TEMPLATE_MAP = {
    "review.assigned": render_review_assigned,
    "approval.requested": render_legal_approval_required,
    "review.escalated": render_escalated_review,
    "sla.breach_warning": render_sla_warning,
    "approval.completed": render_review_approved,
    "workflow.completed": render_review_closed,
}

# Additional template aliases for email-specific routing
TEMPLATE_ALIASES = {
    "email.legal_approval": render_legal_approval_required,
    "email.executive_approval": render_executive_approval_required,
    "email.rejected": render_rejected_review,
    "email.review_closed": render_review_closed,
}
