from flask_babel import refresh as refresh_babel

from app.extensions import db
from app.models.order import Order


def test_login_page_defaults_to_dutch(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert "Aanmelden".encode() in resp.data
    assert "Gebruikersnaam".encode() in resp.data


def test_account_page_switches_dashboard_language(client, admin_user, login):
    login(admin_user)
    resp = client.get("/")
    assert b"Dashboard" in resp.data  # admin_user is pinned to "en"

    resp = client.get("/auth/account")
    resp = client.post(
        "/auth/account",
        data={"full_name": admin_user.full_name, "preferred_language": "fr"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    resp = client.get("/")
    assert "Tableau de bord".encode() in resp.data
    assert "Commandes".encode() in resp.data


def test_portal_locale_follows_client_not_staff_session(client, staff_user, login, demo_client, app):
    demo_client.preferred_language = "fr"
    db.session.commit()
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()

    # A staff member with an English-language session is logged in elsewhere...
    login(staff_user)
    assert staff_user.preferred_language == "en"
    # Flask-Babel caches the resolved locale per request via flask.g; this
    # test's shared app-context fixture makes multiple test-client calls
    # reuse that same g (unlike separate real HTTP requests), so force a
    # fresh evaluation the way a genuinely new request naturally would.
    refresh_babel()

    # ...but the public portal for this order still renders in the client's language.
    resp = client.get(f"/portal/{order.portal_token}")
    assert resp.status_code == 200
    assert b'lang="fr"' in resp.data
    assert "Commande".encode() in resp.data


def test_unsupported_client_language_falls_back_to_shop_default(client, demo_client):
    # "de" isn't one of the app's three supported languages, so an
    # unrecognized portal_locale is ignored and normal fallback applies
    # (no Accept-Language header here -> BABEL_DEFAULT_LOCALE, "nl").
    demo_client.preferred_language = "de"
    db.session.commit()
    order = Order(client_id=demo_client.id)
    db.session.add(order)
    db.session.commit()

    resp = client.get(f"/portal/{order.portal_token}")
    assert resp.status_code == 200
    assert b'lang="nl"' in resp.data
    assert "Bestelling".encode() in resp.data
