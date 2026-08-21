from app.models.user import User


def test_password_hash_roundtrip():
    user = User(username="jane", full_name="Jane Doe", role="staff")
    user.set_password("correct-horse-battery-staple")
    assert user.password_hash != "correct-horse-battery-staple"
    assert user.check_password("correct-horse-battery-staple") is True
    assert user.check_password("wrong-password") is False


def test_login_page_loads(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200


def test_login_success_redirects_to_dashboard(client, admin_user):
    resp = client.post(
        "/auth/login",
        data={"username": "admin", "password": "supersecret123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert resp.request.path == "/"


def test_login_failure_shows_error(client, admin_user):
    resp = client.post(
        "/auth/login",
        data={"username": "admin", "password": "wrong-password"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert resp.request.path == "/auth/login"


def test_dashboard_requires_login(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_logout_clears_session(client, admin_user):
    client.post(
        "/auth/login",
        data={"username": "admin", "password": "supersecret123"},
    )
    resp = client.post("/auth/logout", follow_redirects=False)
    assert resp.status_code == 302
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302


def test_healthz_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
