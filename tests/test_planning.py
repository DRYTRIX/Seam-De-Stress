from datetime import date, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.order import Garment, Order, OrderLine
from app.services.planning import get_daily_loads, load_level


def _order_with_estimated_minutes(client_id, promised_date, minutes, express=False, status="received"):
    order = Order(client_id=client_id, promised_date=promised_date, express=express, status=status)
    db.session.add(order)
    db.session.flush()
    garment = Garment(order_id=order.id, garment_type="other")
    db.session.add(garment)
    db.session.flush()
    # OrderLine.line_total isn't what drives minutes — total_estimated_minutes comes
    # from each line's catalog_item.estimated_minutes, so we need a real catalog item.
    from app.models.catalog import ServiceCatalogItem

    item = ServiceCatalogItem(
        name=f"Task {minutes}",
        category="other",
        default_price=Decimal("10.00"),
        default_vat_rate=Decimal("21.00"),
        estimated_minutes=minutes,
        active=True,
    )
    db.session.add(item)
    db.session.flush()
    db.session.add(
        OrderLine(
            garment_id=garment.id,
            catalog_item_id=item.id,
            description=item.name,
            quantity=1,
            unit_price=item.default_price,
            vat_rate=item.default_vat_rate,
        )
    )
    db.session.commit()
    return order


def test_load_level_thresholds():
    assert load_level(minutes=50, capacity_minutes=240) == "success"
    assert load_level(minutes=200, capacity_minutes=240) == "warning"
    assert load_level(minutes=300, capacity_minutes=240) == "danger"
    assert load_level(minutes=0, capacity_minutes=0) == "danger"


def test_get_daily_loads_sums_minutes_per_day(app, demo_client):
    today = date.today()
    _order_with_estimated_minutes(demo_client.id, today, 100)
    _order_with_estimated_minutes(demo_client.id, today, 50)
    _order_with_estimated_minutes(demo_client.id, today + timedelta(days=1), 30)

    days = get_daily_loads(today, 3, capacity_minutes=240)
    assert days[0]["minutes"] == 150
    assert days[0]["level"] == "success"
    assert days[1]["minutes"] == 30
    assert days[2]["minutes"] == 0
    assert days[2]["orders"] == []


def test_get_daily_loads_excludes_cancelled_orders(app, demo_client):
    today = date.today()
    _order_with_estimated_minutes(demo_client.id, today, 100, status="cancelled")

    days = get_daily_loads(today, 1, capacity_minutes=240)
    assert days[0]["minutes"] == 0


def test_planning_view_requires_login(client):
    resp = client.get("/planning/", follow_redirects=False)
    assert resp.status_code == 302


def test_planning_view_shows_overdue_and_express(client, staff_user, login, demo_client, app):
    login(staff_user)
    yesterday = date.today() - timedelta(days=1)
    overdue_order = _order_with_estimated_minutes(demo_client.id, yesterday, 60, status="in_progress")
    express_order = _order_with_estimated_minutes(demo_client.id, date.today() + timedelta(days=2), 40, express=True)

    resp = client.get("/planning/")
    assert resp.status_code == 200
    assert overdue_order.code.encode() in resp.data
    assert express_order.code.encode() in resp.data
