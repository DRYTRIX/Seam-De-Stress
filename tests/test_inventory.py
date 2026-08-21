from decimal import Decimal

from app.extensions import db
from app.models.inventory import InventoryItem, StockMovement
from app.models.settings import Settings


def _make_item(**overrides):
    defaults = dict(
        name="Trouser zipper 15cm — black",
        category="zippers",
        unit="pcs",
        default_price=Decimal("1.80"),
        default_vat_rate=Decimal("6.00"),
        quantity_on_hand=Decimal("30.00"),
        low_stock_threshold=Decimal("8.00"),
        active=True,
    )
    defaults.update(overrides)
    item = InventoryItem(**defaults)
    db.session.add(item)
    db.session.commit()
    return item


def test_inventory_list_requires_login(client):
    resp = client.get("/inventory/", follow_redirects=False)
    assert resp.status_code == 302


def test_staff_can_view_but_not_create_inventory_item(client, staff_user, login):
    login(staff_user)

    resp = client.get("/inventory/")
    assert resp.status_code == 200

    resp = client.get("/inventory/new")
    assert resp.status_code == 403

    resp = client.post(
        "/inventory/new",
        data={
            "name": "X",
            "category": "zippers",
            "unit": "pcs",
            "default_price": "1.00",
            "default_vat_rate": "21",
        },
    )
    assert resp.status_code == 403


def test_admin_can_create_inventory_item(client, admin_user, login, app):
    login(admin_user)

    resp = client.get("/inventory/new")
    assert resp.status_code == 200

    resp = client.post(
        "/inventory/new",
        data={
            "name": "Bias binding tape (roll)",
            "category": "notions",
            "unit": "roll",
            "description": "For hems and edges.",
            "default_price": "2.80",
            "default_vat_rate": "21",
            "active": "y",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        item = InventoryItem.query.filter_by(name="Bias binding tape (roll)").first()
        assert item is not None
        assert item.default_price == Decimal("2.80")
        assert item.quantity_on_hand == Decimal("0.00")


def test_admin_can_edit_inventory_item_without_touching_quantity(client, admin_user, login, app):
    login(admin_user)
    with app.app_context():
        item = _make_item(quantity_on_hand=Decimal("30.00"))
        item_id = item.id

    resp = client.get(f"/inventory/{item_id}/edit")
    assert resp.status_code == 200

    resp = client.post(
        f"/inventory/{item_id}/edit",
        data={
            "name": "Trouser zipper 15cm — black (updated)",
            "category": "zippers",
            "unit": "pcs",
            "default_price": "2.00",
            "default_vat_rate": "6",
            "active": "y",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        updated = db.session.get(InventoryItem, item_id)
        assert updated.name == "Trouser zipper 15cm — black (updated)"
        assert updated.default_price == Decimal("2.00")
        assert updated.quantity_on_hand == Decimal("30.00")


def test_admin_can_toggle_active(client, admin_user, login, app):
    login(admin_user)
    with app.app_context():
        item = _make_item()
        item_id = item.id

    resp = client.post(f"/inventory/{item_id}/toggle-active", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert db.session.get(InventoryItem, item_id).active is False


def test_inventory_filters_by_category(client, staff_user, login, app):
    with app.app_context():
        _make_item(name="Trouser zipper", category="zippers")
        _make_item(name="Lining fabric", category="fabric")

    login(staff_user)
    resp = client.get("/inventory/?category=fabric")
    assert b"Lining fabric" in resp.data
    assert b"Trouser zipper" not in resp.data


def test_inventory_low_stock_filter(client, staff_user, login, app):
    with app.app_context():
        _make_item(name="Low item", quantity_on_hand=Decimal("2.00"), low_stock_threshold=Decimal("8.00"))
        _make_item(name="Plenty item", quantity_on_hand=Decimal("50.00"), low_stock_threshold=Decimal("8.00"))

    login(staff_user)
    resp = client.get("/inventory/?low_stock=1")
    assert b"Low item" in resp.data
    assert b"Plenty item" not in resp.data


def test_effective_low_stock_threshold_falls_back_to_settings(app):
    with app.app_context():
        item = _make_item(low_stock_threshold=None)
        assert item.effective_low_stock_threshold == Settings.get_solo().default_low_stock_threshold

        item.low_stock_threshold = Decimal("3.00")
        db.session.commit()
        assert item.effective_low_stock_threshold == Decimal("3.00")


def test_is_low_stock_flag(app):
    with app.app_context():
        item = _make_item(quantity_on_hand=Decimal("5.00"), low_stock_threshold=Decimal("8.00"))
        assert item.is_low_stock is True

        item.quantity_on_hand = Decimal("10.00")
        db.session.commit()
        assert item.is_low_stock is False


def test_staff_cannot_receive_or_adjust_stock(client, staff_user, login, app):
    with app.app_context():
        item = _make_item()
        item_id = item.id

    login(staff_user)
    resp = client.post(f"/inventory/{item_id}/receive", data={"quantity": "5"})
    assert resp.status_code == 403

    resp = client.post(f"/inventory/{item_id}/adjust", data={"quantity_delta": "-1", "reason": "waste"})
    assert resp.status_code == 403


def test_admin_can_receive_stock(client, admin_user, login, app):
    login(admin_user)
    with app.app_context():
        item = _make_item(quantity_on_hand=Decimal("30.00"))
        item_id = item.id

    resp = client.post(
        f"/inventory/{item_id}/receive",
        data={"quantity": "10", "note": "New delivery"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        updated = db.session.get(InventoryItem, item_id)
        assert updated.quantity_on_hand == Decimal("40.00")
        movement = StockMovement.query.filter_by(inventory_item_id=item_id).first()
        assert movement.reason == "received"
        assert movement.quantity_delta == Decimal("10.00")


def test_admin_can_adjust_stock_negative_and_positive(client, admin_user, login, app):
    login(admin_user)
    with app.app_context():
        item = _make_item(quantity_on_hand=Decimal("30.00"))
        item_id = item.id

    client.post(f"/inventory/{item_id}/adjust", data={"quantity_delta": "-5", "reason": "waste"})
    with app.app_context():
        assert db.session.get(InventoryItem, item_id).quantity_on_hand == Decimal("25.00")

    client.post(f"/inventory/{item_id}/adjust", data={"quantity_delta": "3", "reason": "adjustment"})
    with app.app_context():
        assert db.session.get(InventoryItem, item_id).quantity_on_hand == Decimal("28.00")


def test_negative_stock_allowed_with_warning(client, admin_user, login, app):
    login(admin_user)
    with app.app_context():
        item = _make_item(quantity_on_hand=Decimal("2.00"))
        item_id = item.id

    resp = client.post(
        f"/inventory/{item_id}/adjust",
        data={"quantity_delta": "-5", "reason": "waste"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Warning" in resp.data

    with app.app_context():
        assert db.session.get(InventoryItem, item_id).quantity_on_hand == Decimal("-3.00")
