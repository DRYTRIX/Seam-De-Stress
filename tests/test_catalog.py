from decimal import Decimal

from app.extensions import db
from app.models.catalog import ServiceCatalogItem


def _make_item(**overrides):
    defaults = dict(
        name="Trouser hem",
        category="hems",
        default_price=Decimal("12.00"),
        default_vat_rate=Decimal("21.00"),
        estimated_minutes=20,
        active=True,
    )
    defaults.update(overrides)
    item = ServiceCatalogItem(**defaults)
    db.session.add(item)
    db.session.commit()
    return item


def test_catalog_list_requires_login(client):
    resp = client.get("/catalog/", follow_redirects=False)
    assert resp.status_code == 302


def test_staff_can_view_but_not_create_catalog_item(client, staff_user, login):
    login(staff_user)

    resp = client.get("/catalog/")
    assert resp.status_code == 200

    resp = client.get("/catalog/new")
    assert resp.status_code == 403

    resp = client.post(
        "/catalog/new",
        data={"name": "X", "category": "hems", "default_price": "10.00", "default_vat_rate": "21", "estimated_minutes": "10"},
    )
    assert resp.status_code == 403


def test_admin_can_create_catalog_item(client, admin_user, login, app):
    login(admin_user)

    resp = client.post(
        "/catalog/new",
        data={
            "name": "Replace zipper",
            "category": "zippers",
            "description": "Standard trouser zipper replacement.",
            "default_price": "14.00",
            "default_vat_rate": "6",
            "estimated_minutes": "25",
            "active": "y",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        item = ServiceCatalogItem.query.filter_by(name="Replace zipper").first()
        assert item is not None
        assert item.default_price == Decimal("14.00")
        assert item.category == "zippers"


def test_admin_can_edit_catalog_item(client, admin_user, login, app):
    login(admin_user)
    with app.app_context():
        item = _make_item(name="Trouser hem", category="hems", default_price=Decimal("12.00"))
        item_id = item.id

    resp = client.get(f"/catalog/{item_id}/edit")
    assert resp.status_code == 200
    assert b"Trouser hem" in resp.data

    resp = client.post(
        f"/catalog/{item_id}/edit",
        data={
            "name": "Trouser hem (updated)",
            "category": "hems",
            "default_price": "15.00",
            "default_vat_rate": "21",
            "estimated_minutes": "20",
            "active": "y",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        updated = db.session.get(ServiceCatalogItem, item_id)
        assert updated.name == "Trouser hem (updated)"
        assert updated.default_price == Decimal("15.00")


def test_admin_can_toggle_active(client, admin_user, login, app):
    login(admin_user)
    with app.app_context():
        item = _make_item()
        item_id = item.id

    resp = client.post(f"/catalog/{item_id}/toggle-active", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert db.session.get(ServiceCatalogItem, item_id).active is False


def test_catalog_filters_by_category(client, staff_user, login, app):
    with app.app_context():
        _make_item(name="Trouser hem", category="hems")
        _make_item(name="Replace zipper", category="zippers", default_vat_rate=Decimal("6.00"))

    login(staff_user)
    resp = client.get("/catalog/?category=zippers")
    assert b"Replace zipper" in resp.data
    assert b"Trouser hem" not in resp.data
