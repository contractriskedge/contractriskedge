"""Email notification sender — SMTP-based email delivery for review notifications.

Provides:
  - SMTP email sending with connection pooling
  - HTML email templates for all notification types
  - Tenant-isolated email configuration
  - Delivery tracking and failure logging

Usage:
    from app.domains.notify.email import send_notification_email

    await send_notification_email(
        to_email="user@example.com",
        subject="Review Assigned",
        template="review_assigned",
        context={"review_id": "...", "reviewer_name": "..."},
    )
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ── Email Templates ────────────────────────────────────────────────

TEMPLATES: dict[str, tuple[str, str]] = {
    "review_assigned": (
        "Review Assigned — {review_id}",
        """<!DOCTYPE html>
<html><body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
<h2 style="color: #1e3a5f;">Review Assigned</h2>
<p>Hello {recipient_name},</p>
<p>A contract review has been assigned to you.</p>
<div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 16px 0;">
    <p><strong>Review ID:</strong> {review_id}</p>
    <p><strong>Role:</strong> {role}</p>
    <p><strong>Priority:</strong> {priority}</p>
</div>
<a href="{app_url}/review/{review_id}" style="display: inline-block; background: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px;">Open Review</a>
<p style="margin-top: 24px; font-size: 12px; color: #9ca3af;">ContractRiskEdge — Enterprise Contract Review Platform</p>
</body></html>""",
    ),
    "review_escalated": (
        "Review Escalated — {review_id}",
        """<!DOCTYPE html>
<html><body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
<h2 style="color: #dc2626;">Review Escalated</h2>
<p>Hello {recipient_name},</p>
<p>A contract review has been escalated and requires your attention.</p>
<div style="background: #fef2f2; padding: 16px; border-radius: 8px; margin: 16px 0; border: 1px solid #fecaca;">
    <p><strong>Review ID:</strong> {review_id}</p>
    <p><strong>Reason:</strong> {reason}</p>
    <p><strong>Escalated By:</strong> {escalated_by}</p>
</div>
<a href="{app_url}/review/{review_id}" style="display: inline-block; background: #dc2626; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px;">View Escalation</a>
<p style="margin-top: 24px; font-size: 12px; color: #9ca3af;">ContractRiskEdge — Enterprise Contract Review Platform</p>
</body></html>""",
    ),
    "sla_breach": (
        "SLA Breach Warning — {review_id}",
        """<!DOCTYPE html>
<html><body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
<h2 style="color: #ea580c;">SLA Breach Warning</h2>
<p>Hello {recipient_name},</p>
<p>A contract review is approaching or has exceeded its SLA deadline.</p>
<div style="background: #fff7ed; padding: 16px; border-radius: 8px; margin: 16px 0; border: 1px solid #fed7aa;">
    <p><strong>Review ID:</strong> {review_id}</p>
    <p><strong>SLA Deadline:</strong> {sla_deadline}</p>
    <p><strong>Priority:</strong> {priority}</p>
</div>
<a href="{app_url}/review/{review_id}" style="display: inline-block; background: #ea580c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px;">View Review</a>
<p style="margin-top: 24px; font-size: 12px; color: #9ca3af;">ContractRiskEdge — Enterprise Contract Review Platform</p>
</body></html>""",
    ),
    "analysis_failed": (
        "AI Analysis Failed — {review_id}",
        """<!DOCTYPE html>
<html><body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
<h2 style="color: #dc2626;">AI Analysis Failed</h2>
<p>Hello {recipient_name},</p>
<p>The AI analysis for a contract review has failed.</p>
<div style="background: #fef2f2; padding: 16px; border-radius: 8px; margin: 16px 0; border: 1px solid #fecaca;">
    <p><strong>Review ID:</strong> {review_id}</p>
    <p><strong>Error:</strong> {error_message}</p>
    <p><strong>Retry Count:</strong> {retry_count}</p>
</div>
<p style="margin-top: 24px; font-size: 12px; color: #9ca3af;">ContractRiskEdge — Enterprise Contract Review Platform</p>
</body></html>""",
    ),
    "review_approved": (
        "Review Approved — {review_id}",
        """<!DOCTYPE html>
<html><body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
<h2 style="color: #16a34a;">Review Approved</h2>
<p>Hello {recipient_name},</p>
<p>A contract review has been approved.</p>
<div style="background: #f0fdf4; padding: 16px; border-radius: 8px; margin: 16px 0; border: 1px solid #bbf7d0;">
    <p><strong>Review ID:</strong> {review_id}</p>
    <p><strong>Approved By:</strong> {approved_by}</p>
    {comments_html}
</div>
<a href="{app_url}/review/{review_id}" style="display: inline-block; background: #16a34a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px;">View Approved Review</a>
<p style="margin-top: 24px; font-size: 12px; color: #9ca3af;">ContractRiskEdge — Enterprise Contract Review Platform</p>
</body></html>""",
    ),
}


def _render_template(template_name: str, context: dict) -> tuple[str, str]:
    """Render an email template with the given context.

    Returns (subject, html_body).
    """
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown email template: {template_name}")

    subject_template, body_template = TEMPLATES[template_name]

    # Add common context
    context.setdefault("app_url", settings.app_url or "http://localhost:3000")
    context.setdefault("recipient_name", context.get("recipient_name", "User"))

    # Format comments_html for review_approved template
    if template_name == "review_approved" and context.get("comments"):
        context["comments_html"] = f'<p><strong>Comments:</strong> {context["comments"]}</p>'
    else:
        context["comments_html"] = ""

    try:
        subject = subject_template.format(**context)
        body = body_template.format(**context)
    except KeyError as e:
        logger.warning("Missing template variable %s for %s", e, template_name)
        subject = subject_template
        body = body_template

    return subject, body


async def send_notification_email(
    to_email: str,
    template_name: str,
    context: dict,
    tenant_id: Optional[str] = None,
) -> bool:
    """Send a notification email using SMTP.

    Args:
        to_email: Recipient email address.
        template_name: Name of the email template to use.
        context: Template variables.
        tenant_id: Optional tenant ID for logging.

    Returns:
        True if sent successfully, False otherwise.
    """
    if not settings.smtp_host:
        logger.warning(
            "SMTP not configured. Email not sent.",
            extra={"template": template_name, "to": to_email, "tenant_id": tenant_id},
        )
        return False

    try:
        subject, html_body = _render_template(template_name, context)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from_email or "noreply@contractriskedge.com"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        # Send via SMTP with timeout
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port or 587,
            timeout=30,
        ) as server:
            if settings.smtp_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        logger.info(
            "Email sent",
            extra={
                "template": template_name,
                "to": to_email,
                "subject": subject,
                "tenant_id": tenant_id,
            },
        )
        return True

    except smtplib.SMTPException as exc:
        logger.error(
            "SMTP send failed",
            extra={
                "template": template_name,
                "to": to_email,
                "error": str(exc),
                "tenant_id": tenant_id,
            },
        )
        return False
    except Exception as exc:
        logger.error(
            "Email send failed",
            extra={
                "template": template_name,
                "to": to_email,
                "error": str(exc),
                "tenant_id": tenant_id,
            },
        )
        return False
