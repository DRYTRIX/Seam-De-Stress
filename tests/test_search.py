from app.extensions import db
from app.models.order import Garment, Order


def test_search_requires_login(client):
    resp = client.get("/search?q=sofie", follow_redirects=False)
    assert resp.status_code == 302


def test_search_finds_client_by_name(client, staff_user, login, demo_client):
    login(staff_user)
    resp = client.get(f"/search?q={demo_client.name.split()[0]}")
    assert resp.status_code == 200
    assert demo_client.name.encode() in resp.data


def test_search_finds_order_by_code(client, staff_user, login, demo_client):
    login(staff_user)
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()

    resp = client.get(f"/search?q={order.code}")
    assert order.code.encode() in resp.data


def test_search_finds_order_by_client_name(client, staff_user, login, demo_client):
    login(staff_user)
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()

    resp = client.get(f"/search?q={demo_client.name.split()[0]}")
    assert order.code.encode() in resp.data


def test_search_finds_garment_by_description(client, staff_user, login, demo_client):
    login(staff_user)
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.flush()
    garment = Garment(order_id=order.id, garment_type="jacket", brand="Levi's", description="Vintage denim jacket")
    db.session.add(garment)
    db.session.commit()

    resp = client.get("/search?q=denim")
    assert order.code.encode() in resp.data


def test_search_with_no_query_shows_prompt_not_error(client, staff_user, login):
    login(staff_user)
    resp = client.get("/search")
    assert resp.status_code == 200


def test_search_with_no_matches_shows_empty_state(client, staff_user, login):
    login(staff_user)
    resp = client.get("/search?q=zzz-no-such-thing-zzz")
    assert resp.status_code == 200
    assert b"No results" in resp.data
