from decimal import Decimal

from app.extensions import db
from app.models.order import Garment, Order, OrderLine


def _make_order_with_lines(client_id, lines):
    """lines: list of (unit_price, quantity, vat_rate) tuples."""
    order = Order(client_id=client_id, status="received", payment_status="unpaid")
    db.session.add(order)
    db.session.flush()

    garment = Garment(order_id=order.id, garment_type="trousers")
    db.session.add(garment)
    db.session.flush()

    for unit_price, quantity, vat_rate in lines:
        db.session.add(
            OrderLine(
                garment_id=garment.id,
                description="Line",
                quantity=quantity,
                unit_price=Decimal(unit_price),
                vat_rate=Decimal(vat_rate),
            )
        )
    db.session.commit()
    return order


def test_order_code_is_derived_from_id(app, demo_client):
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()
    assert order.code == f"SDS-{order.id:05d}"


def test_line_total_and_vat_amount(app, demo_client):
    order = _make_order_with_lines(demo_client.id, [("12.00", 1, "21.00")])
    line = order.garments[0].lines[0]
    assert line.line_total == Decimal("12.00")
    assert line.vat_amount == Decimal("2.52")
    assert line.line_total_with_vat == Decimal("14.52")


def test_line_total_multiplies_by_quantity(app, demo_client):
    order = _make_order_with_lines(demo_client.id, [("3.00", 2, "6.00")])
    line = order.garments[0].lines[0]
    assert line.line_total == Decimal("6.00")
    assert line.vat_amount == Decimal("0.36")


def test_order_aggregates_across_garments_and_lines(app, demo_client):
    order = _make_order_with_lines(demo_client.id, [("12.00", 1, "21.00"), ("14.00", 1, "6.00")])
    # add a second garment with its own line
    garment2 = Garment(order_id=order.id, garment_type="dress")
    db.session.add(garment2)
    db.session.flush()
    db.session.add(
        OrderLine(garment_id=garment2.id, description="Dress hem", quantity=1, unit_price=Decimal("18.00"), vat_rate=Decimal("21.00"))
    )
    db.session.commit()

    assert order.subtotal == Decimal("44.00")
    assert order.vat_total == Decimal("2.52") + Decimal("0.84") + Decimal("3.78")
    assert order.total == order.subtotal + order.vat_total


def test_order_with_no_lines_has_zero_totals(app, demo_client):
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()
    assert order.subtotal == Decimal("0.00")
    assert order.vat_total == Decimal("0.00")
    assert order.total == Decimal("0.00")


def test_order_is_overdue_only_when_past_due_and_not_finished(app, demo_client):
    from datetime import date, timedelta

    past = date.today() - timedelta(days=1)
    future = date.today() + timedelta(days=1)

    overdue = Order(client_id=demo_client.id, promised_date=past, status="in_progress")
    not_overdue_future = Order(client_id=demo_client.id, promised_date=future, status="in_progress")
    finished_but_late = Order(client_id=demo_client.id, promised_date=past, status="picked_up")
    db.session.add_all([overdue, not_overdue_future, finished_but_late])
    db.session.commit()

    assert overdue.is_overdue is True
    assert not_overdue_future.is_overdue is False
    assert finished_but_late.is_overdue is False
