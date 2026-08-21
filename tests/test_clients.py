from app.models.client import Client


def test_clients_list_requires_login(client):
    resp = client.get("/clients/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_staff_can_create_and_view_client(client, staff_user, login):
    login(staff_user)

    resp = client.post(
        "/clients/new",
        data={
            "name": "Sofie Peeters",
            "phone": "+32 470 12 34 56",
            "email": "sofie@example.com",
            "address": "Kerkstraat 1, 2000 Antwerpen",
            "preferred_language": "nl",
            "notes": "Always hems 2 cm shorter.",
            "consent_notifications": "y",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Sofie Peeters" in resp.data

    created = Client.query.filter_by(name="Sofie Peeters").first()
    assert created is not None
    assert created.consent_notifications is True


def test_create_client_requires_name(client, staff_user, login):
    login(staff_user)
    resp = client.post("/clients/new", data={"name": "", "preferred_language": "nl"})
    assert resp.status_code == 200
    assert Client.query.count() == 0


def test_edit_client_updates_fields(client, staff_user, login, app):
    from app.extensions import db

    with app.app_context():
        c = Client(name="Old Name", preferred_language="nl", consent_notifications=True)
        db.session.add(c)
        db.session.commit()
        client_id = c.id

    login(staff_user)
    resp = client.post(
        f"/clients/{client_id}/edit",
        data={"name": "New Name", "preferred_language": "fr", "consent_notifications": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"New Name" in resp.data

    updated = db.session.get(Client, client_id)
    assert updated.name == "New Name"
    assert updated.preferred_language == "fr"
    assert updated.consent_notifications is False


def test_client_search_filters_results(client, staff_user, login, app):
    from app.extensions import db

    with app.app_context():
        db.session.add_all(
            [
                Client(name="Sofie Peeters", preferred_language="nl"),
                Client(name="Marie Lefebvre", preferred_language="fr"),
            ]
        )
        db.session.commit()

    login(staff_user)
    resp = client.get("/clients/?q=Sofie")
    assert b"Sofie Peeters" in resp.data
    assert b"Marie Lefebvre" not in resp.data
