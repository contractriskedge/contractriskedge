"""Generic email service — provider-independent email delivery."""
from .service import EmailService, EmailSender, EmailTemplate

__all__ = ["EmailService", "EmailSender", "EmailTemplate"]
