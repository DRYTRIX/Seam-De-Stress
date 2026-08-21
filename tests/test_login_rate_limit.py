import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db
from app.models.user import User


class RateLimitedTestingConfig(TestingConfig):
    RATELIMIT_ENABLED = True
    LOGIN_RATE_LIMIT = "3 per minute"


@pytest.fixture()
def rate_limited_client():
    application = create_app(RateLimitedTestingConfig)
    with application.app_context():
        _db.create_all()
        user = User(username="admin", full_name="Shop Owner", role="admin")
        user.set_password("supersecret123")
        _db.session.add(user)
        _db.session.commit()
        yield application.test_client()
        _db.drop_all()


def test_login_is_rate_limited_after_repeated_attempts(rate_limited_client):
    for _ in range(3):
        resp = rate_limited_client.post(
            "/auth/login", data={"username": "admin", "password": "wrong"}
        )
        assert resp.status_code == 200

    throttled = rate_limited_client.post(
        "/auth/login", data={"username": "admin", "password": "wrong"}
    )
    assert throttled.status_code == 429
