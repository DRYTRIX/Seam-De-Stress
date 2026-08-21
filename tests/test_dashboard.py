from datetime import date, timedelta

from app.extensions import db
from app.models.order import Order, OrderStatusLog


def test_dashboard_requires_login(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302


def test_dashboard_shows_counts_and_quick_action(client, staff_user, login, demo_client, app):
    login(staff_user)

    order = Order(client_id=demo_client.id, promised_date=date.today(), status="in_progress")
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderStatusLog(order_id=order.id, user_id=staff_user.id, from_status="received", to_status="in_progress"))
    db.session.commit()

    resp = client.get("/")
    assert resp.status_code == 200
    assert order.code.encode() in resp.data
    assert b"Mark Ready for pickup" in resp.data


def test_dashboard_overdue_section_only_shows_when_present(client, staff_user, login, demo_client, app):
    overdue_panel_heading = b'<h2 class="h6 fw-bold mb-0">Overdue</h2>'

    login(staff_user)
    resp = client.get("/")
    assert overdue_panel_heading not in resp.data

    order = Order(client_id=demo_client.id, promised_date=date.today() - timedelta(days=2), status="received")
    db.session.add(order)
    db.session.commit()

    resp = client.get("/")
    assert overdue_panel_heading in resp.data
    assert order.code.encode() in resp.data
