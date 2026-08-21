import smtplib
from email.message import EmailMessage

from flask import current_app, url_for

from app.extensions import db
from app.models.order import NotificationLog
from app.notification_templates import NOTIFICATION_TEMPLATES, PORTAL_LINE


class NotificationError(Exception):
    """Raised when a channel can't deliver — always caught and logged, never
    left to bubble up and break the caller's request."""


class NotificationChannel:
    key = None

    def send(self, *, to, subject, body):
        raise NotImplementedError


class EmailChannel(NotificationChannel):
    key = "email"

    def send(self, *, to, subject, body):
        host = current_app.config.get("SMTP_HOST")
        if not host:
            raise NotificationError("SMTP is not configured (SMTP_HOST is empty).")
        if not to:
            raise NotificationError("Recipient has no email address on file.")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = current_app.config.get("SMTP_FROM_ADDRESS") or current_app.config.get("SMTP_USERNAME") or "no-reply@localhost"
        message["To"] = to
        message.set_content(body)

        port = current_app.config.get("SMTP_PORT", 587)
        username = current_app.config.get("SMTP_USERNAME")
        password = current_app.config.get("SMTP_PASSWORD")
        use_tls = current_app.config.get("SMTP_USE_TLS", True)

        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(message)


# Registry so a future channel (e.g. SMS via Twilio) is a new class + one line here.
CHANNELS = {"email": EmailChannel()}


def render_notification(template_key, language, **placeholders):
    templates = NOTIFICATION_TEMPLATES[template_key]
    template = templates.get(language) or templates["en"]
    subject = template["subject"].format(**placeholders)
    body = template["body"].format(**placeholders)
    return subject, body


def notify_order_ready(order):
    """Email the client that their order is ready, logging the attempt on
    the order regardless of outcome. Returns the NotificationLog row."""
    client = order.client
    language = client.preferred_language or "nl"

    portal_line = ""
    if order.portal_active:
        portal_url = url_for("portal.view", token=order.portal_token, _external=True)
        portal_line = PORTAL_LINE.get(language, PORTAL_LINE["en"]).format(portal_url=portal_url)

    subject, body = render_notification(
        "order_ready",
        language,
        client_name=client.name,
        order_code=order.code,
        shop_name=current_app.config["APP_NAME"],
        portal_line=portal_line,
    )

    log = NotificationLog(
        order_id=order.id,
        channel="email",
        template_key="order_ready",
        recipient=client.email,
        language=language,
        status="sent",
    )
    try:
        CHANNELS["email"].send(to=client.email, subject=subject, body=body)
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)

    db.session.add(log)
    db.session.commit()
    return log
