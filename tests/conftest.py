import pytest

from app import create_app
from app.extensions import db as _db
from app.models.user import User


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def admin_user(app):
    # preferred_language pinned to "en" so route/template tests can assert on
    # literal English copy regardless of the model's "nl" default.
    user = User(
        username="admin",
        email="admin@example.com",
        full_name="Shop Owner",
        role="admin",
        preferred_language="en",
    )
    user.set_password("supersecret123")
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture()
def staff_user(app):
    user = User(
        username="staff",
        email="staff@example.com",
        full_name="Staff Member",
        role="staff",
        preferred_language="en",
    )
    user.set_password("supersecret123")
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture()
def login(client):
    def _login(user):
        return client.post(
            "/auth/login",
            data={"username": user.username, "password": "supersecret123"},
            follow_redirects=True,
        )

    return _login


@pytest.fixture()
def demo_client(app):
    from app.models.client import Client

    c = Client(name="Sofie Peeters", phone="+32 470 12 34 56", preferred_language="nl")
    _db.session.add(c)
    _db.session.commit()
    return c


@pytest.fixture()
def catalog_item(app):
    from decimal import Decimal

    from app.models.catalog import ServiceCatalogItem

    item = ServiceCatalogItem(
        name="Trouser hem (machine stitch)",
        category="hems",
        default_price=Decimal("12.00"),
        default_vat_rate=Decimal("21.00"),
        estimated_minutes=20,
        active=True,
    )
    _db.session.add(item)
    _db.session.commit()
    return item


@pytest.fixture()
def inventory_item(app):
    from decimal import Decimal

    from app.models.inventory import InventoryItem

    item = InventoryItem(
        name="Invisible zipper 20cm — black",
        category="zippers",
        unit="pcs",
        default_price=Decimal("2.20"),
        default_vat_rate=Decimal("6.00"),
        quantity_on_hand=Decimal("25.00"),
        low_stock_threshold=Decimal("8.00"),
        active=True,
    )
    _db.session.add(item)
    _db.session.commit()
    return item


@pytest.fixture()
def sample_jpeg_bytes():
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (800, 600), color=(120, 50, 200)).save(buf, format="JPEG")
    buf.seek(0)
    return buf
