import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import Notification

logger = logging.getLogger(__name__)


def notify(recipients, *, kind, title, message="", url=""):
    """Create in-app notifications (and optional emails) for active users."""
    users = [u for u in recipients if u.is_active]
    if not users:
        return []
    created = Notification.objects.bulk_create(
        [Notification(recipient=u, kind=kind, title=title[:200], message=message, url=url) for u in users]
    )
    if settings.SB_EMAIL_NOTIFICATIONS:
        emails = [u.email for u in users if u.email]
        transaction.on_commit(lambda: _send_emails(emails, title, message, url))
    return created


def _send_emails(emails, title, message, url):
    link = f"{settings.SB_SITE_URL.rstrip('/')}{url}" if url else ""
    body = "\n\n".join(part for part in (message, link) if part)
    for email in emails:
        try:
            send_mail(f"[{settings.SB_SITE_NAME}] {title}", body, None, [email])
        except Exception:  # pragma: no cover - network failures should not break requests
            logger.exception("Failed to send notification email")
