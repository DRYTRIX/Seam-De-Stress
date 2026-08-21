from app.models.settings import DEFAULT_DAILY_CAPACITY_MINUTES, Settings


def test_get_solo_creates_defaults_on_first_access(app):
    settings = Settings.get_solo()
    assert settings.id == 1
    assert settings.daily_capacity_minutes == DEFAULT_DAILY_CAPACITY_MINUTES


def test_get_solo_is_idempotent(app):
    first = Settings.get_solo()
    second = Settings.get_solo()
    assert first.id == second.id
    assert Settings.query.count() == 1


def test_settings_requires_login(client):
    resp = client.get("/settings/", follow_redirects=False)
    assert resp.status_code == 302


def test_staff_cannot_access_settings(client, staff_user, login):
    login(staff_user)
    resp = client.get("/settings/")
    assert resp.status_code == 403


def test_admin_can_update_daily_capacity(client, admin_user, login, app):
    login(admin_user)
    resp = client.post(
        "/settings/",
        data={"daily_capacity_minutes": "300", "default_low_stock_threshold": "5"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert Settings.get_solo().daily_capacity_minutes == 300
