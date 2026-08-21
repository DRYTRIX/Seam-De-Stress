from app.models.catalog import ServiceCatalogItem
from app.models.client import Client
from app.models.inventory import InventoryItem
from app.models.invoice import Invoice
from app.models.order import Order, OrderLine
from app.models.user import User


def test_seed_creates_demo_data(runner, app):
    result = runner.invoke(args=["seed"])
    assert result.exit_code == 0, result.output

    with app.app_context():
        assert User.query.filter_by(username="admin").count() == 1
        assert ServiceCatalogItem.query.count() == 31
        assert InventoryItem.query.count() == 15
        assert Client.query.count() == 8
        assert Order.query.count() == 6
        assert Invoice.query.count() == 1
        assert OrderLine.query.filter(OrderLine.inventory_item_id.isnot(None)).count() == 1


def test_seed_is_idempotent(runner, app):
    runner.invoke(args=["seed"])
    with app.app_context():
        first_user_count = User.query.count()
        first_client_count = Client.query.count()
        first_order_count = Order.query.count()

    result = runner.invoke(args=["seed"])
    assert result.exit_code == 0

    with app.app_context():
        assert User.query.count() == first_user_count
        assert Client.query.count() == first_client_count
        assert Order.query.count() == first_order_count
        assert "already exists" in result.output or "already exist" in result.output or "already has" in result.output
