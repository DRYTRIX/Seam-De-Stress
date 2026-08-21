from app.extensions import db
from app.models.order import Order
from app.models.settings import Settings


def test_portal_view_requires_no_login(client, demo_client):
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()

    resp = client.get(f"/portal/{order.portal_token}")
    assert resp.status_code == 200
    assert order.code.encode() in resp.data


def test_portal_view_404s_for_unknown_token(client):
    resp = client.get("/portal/does-not-exist")
    assert resp.status_code == 404


def test_portal_view_404s_when_revoked(client, demo_client):
    order = Order(client_id=demo_client.id, portal_revoked=True)
    db.session.add(order)
    db.session.commit()

    resp = client.get(f"/portal/{order.portal_token}")
    assert resp.status_code == 404


def test_portal_hides_prices_when_setting_disabled(client, demo_client):
    settings = Settings.get_solo()
    settings.portal_show_prices = False
    db.session.commit()

    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()

    resp = client.get(f"/portal/{order.portal_token}")
    assert b"Total (incl. VAT)" not in resp.data


def test_new_order_gets_a_portal_token_automatically(client, staff_user, login, demo_client):
    login(staff_user)
    client.post(
        "/orders/new",
        data={"client_id": demo_client.id, "promised_date": "", "express": ""},
        follow_redirects=True,
    )
    order = Order.query.order_by(Order.id.desc()).first()
    assert order.portal_token is not None
    assert order.portal_active is True


def test_revoke_and_regenerate_portal_link(client, staff_user, login, demo_client):
    login(staff_user)
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()
    original_token = order.portal_token

    resp = client.post(f"/orders/{order.id}/portal/revoke", follow_redirects=True)
    assert resp.status_code == 200
    assert db.session.get(Order, order.id).portal_revoked is True

    public = client.get(f"/portal/{original_token}")
    assert public.status_code == 404

    resp = client.post(f"/orders/{order.id}/portal/regenerate", follow_redirects=True)
    assert resp.status_code == 200
    refreshed = db.session.get(Order, order.id)
    assert refreshed.portal_revoked is False
    assert refreshed.portal_token != original_token

    public = client.get(f"/portal/{refreshed.portal_token}")
    assert public.status_code == 200
