from unittest.mock import MagicMock, patch

from app.extensions import db
from app.models.order import NotificationLog, Order
from app.services.notifications import notify_order_ready, render_notification


def test_render_notification_fills_placeholders_per_language():
    subject, body = render_notification(
        "order_ready", "nl", client_name="Sofie", order_code="SDS-00007", shop_name="Shop", portal_line=""
    )
    assert "SDS-00007" in subject
    assert "Sofie" in body

    subject_en, _ = render_notification(
        "order_ready", "en", client_name="Sofie", order_code="SDS-00007", shop_name="Shop", portal_line=""
    )
    assert "ready" in subject_en.lower()


def test_render_notification_falls_back_to_english_for_unknown_language():
    subject, _ = render_notification(
        "order_ready", "de", client_name="Sofie", order_code="SDS-1", shop_name="Shop", portal_line=""
    )
    assert "ready" in subject.lower()


def test_notify_client_blocked_without_consent(client, staff_user, login, demo_client, app):
    demo_client.consent_notifications = False
    demo_client.email = "sofie@example.com"
    db.session.commit()

    login(staff_user)
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()

    resp = client.post(f"/orders/{order.id}/notify", follow_redirects=True)
    assert resp.status_code == 200
    assert NotificationLog.query.filter_by(order_id=order.id).count() == 0
    assert b"opted out" in resp.data


def test_notify_client_blocked_without_email(client, staff_user, login, demo_client, app):
    demo_client.consent_notifications = True
    demo_client.email = None
    db.session.commit()

    login(staff_user)
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()

    resp = client.post(f"/orders/{order.id}/notify", follow_redirects=True)
    assert resp.status_code == 200
    assert NotificationLog.query.filter_by(order_id=order.id).count() == 0
    assert b"no email address" in resp.data


def test_notify_client_logs_failure_when_smtp_unconfigured(client, staff_user, login, demo_client, app):
    demo_client.consent_notifications = True
    demo_client.email = "sofie@example.com"
    db.session.commit()

    login(staff_user)
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()

    assert app.config["SMTP_HOST"] == ""

    resp = client.post(f"/orders/{order.id}/notify", follow_redirects=True)
    assert resp.status_code == 200

    log = NotificationLog.query.filter_by(order_id=order.id).first()
    assert log is not None
    assert log.status == "failed"
    assert log.channel == "email"
    assert log.template_key == "order_ready"
    assert "SMTP" in log.error_message


def test_notify_order_ready_logs_sent_when_smtp_configured(app, demo_client):
    demo_client.consent_notifications = True
    demo_client.email = "sofie@example.com"
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()

    app.config["SMTP_HOST"] = "smtp.example.com"
    app.config["SMTP_FROM_ADDRESS"] = "shop@example.com"
    try:
        with app.test_request_context("/"), patch("app.services.notifications.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value.__enter__.return_value = mock_server

            log = notify_order_ready(order)

            assert log.status == "sent"
            assert log.recipient == "sofie@example.com"
            mock_server.send_message.assert_called_once()
            sent_message = mock_server.send_message.call_args[0][0]
            assert sent_message["To"] == "sofie@example.com"
            assert order.code in str(sent_message["Subject"])
    finally:
        app.config["SMTP_HOST"] = ""
