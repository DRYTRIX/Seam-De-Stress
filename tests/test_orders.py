import os
from decimal import Decimal

from app.extensions import db
from app.models.inventory import InventoryItem, StockMovement
from app.models.order import Garment, GarmentPhoto, Order, OrderLine, OrderStatusLog


def _create_order(client, staff_user, login, demo_client, promised_date="2026-09-01", express=False):
    login(staff_user)
    resp = client.post(
        "/orders/new",
        data={
            "client_id": demo_client.id,
            "promised_date": promised_date,
            "express": "y" if express else "",
            "internal_notes": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200, resp.data
    order = Order.query.order_by(Order.id.desc()).first()
    return order


def test_orders_list_requires_login(client):
    resp = client.get("/orders/", follow_redirects=False)
    assert resp.status_code == 302


def test_create_order_sets_received_status_and_logs(client, staff_user, login, demo_client, app):
    order = _create_order(client, staff_user, login, demo_client, express=True)
    assert order.status == "received"
    assert order.payment_status == "unpaid"
    assert order.express is True

    logs = OrderStatusLog.query.filter_by(order_id=order.id).all()
    assert len(logs) == 1
    assert logs[0].from_status is None
    assert logs[0].to_status == "received"


def test_order_code_appears_on_list_page(client, staff_user, login, demo_client):
    order = _create_order(client, staff_user, login, demo_client)
    resp = client.get("/orders/")
    assert order.code.encode() in resp.data


def test_add_garment_with_photo(client, staff_user, login, demo_client, sample_jpeg_bytes, app):
    order = _create_order(client, staff_user, login, demo_client)

    resp = client.post(
        f"/orders/{order.id}/garments/new",
        data={
            "garment_type": "trousers",
            "color": "Black",
            "brand": "Levi's",
            "description": "Slim fit",
            "measurements_notes": "inseam 80cm",
            "photo": (sample_jpeg_bytes, "test.jpg"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Black" in resp.data

    garment = Garment.query.filter_by(order_id=order.id).first()
    assert garment is not None
    photo = GarmentPhoto.query.filter_by(garment_id=garment.id).first()
    assert photo is not None
    assert os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], photo.filename))
    assert os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], photo.thumbnail_filename))


def test_add_line_from_catalog_item(client, staff_user, login, demo_client, catalog_item, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/garments/new", data={"garment_type": "trousers"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order.id).first()

    resp = client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines",
        data={
            "catalog_item_id": str(catalog_item.id),
            "description": catalog_item.name,
            "quantity": "1",
            "unit_price": str(catalog_item.default_price),
            "vat_rate": str(catalog_item.default_vat_rate),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert catalog_item.name.encode() in resp.data

    line = OrderLine.query.filter_by(garment_id=garment.id).first()
    assert line is not None
    assert line.catalog_item_id == catalog_item.id


def test_add_custom_line_without_catalog_item(client, staff_user, login, demo_client, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/garments/new", data={"garment_type": "other"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order.id).first()

    resp = client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines",
        data={"catalog_item_id": "", "description": "One-off repair", "quantity": "1", "unit_price": "9.50", "vat_rate": "21"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    line = OrderLine.query.filter_by(garment_id=garment.id).first()
    assert line is not None
    assert line.catalog_item_id is None
    assert line.description == "One-off repair"


def test_status_transition_and_invalid_status(client, staff_user, login, demo_client, app):
    order = _create_order(client, staff_user, login, demo_client)

    resp = client.post(f"/orders/{order.id}/status", data={"status": "in_progress"}, follow_redirects=True)
    assert resp.status_code == 200
    assert db.session.get(Order, order.id).status == "in_progress"
    assert OrderStatusLog.query.filter_by(order_id=order.id).count() == 2

    resp = client.post(f"/orders/{order.id}/status", data={"status": "not-a-real-status"})
    assert resp.status_code == 400


def test_payment_status_update(client, staff_user, login, demo_client, app):
    order = _create_order(client, staff_user, login, demo_client)
    resp = client.post(f"/orders/{order.id}/payment-status", data={"payment_status": "paid"}, follow_redirects=True)
    assert resp.status_code == 200
    assert db.session.get(Order, order.id).payment_status == "paid"


def test_garment_ticket_contains_qr_code(client, staff_user, login, demo_client, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/garments/new", data={"garment_type": "dress"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order.id).first()

    resp = client.get(f"/orders/{order.id}/garments/{garment.id}/ticket")
    assert resp.status_code == 200
    assert b"data:image/png;base64" in resp.data
    assert order.code.encode() in resp.data


def test_receipt_includes_portal_qr_when_link_active(client, staff_user, login, demo_client, app):
    order = _create_order(client, staff_user, login, demo_client)
    resp = client.get(f"/orders/{order.id}/receipt")
    assert resp.status_code == 200
    assert b"data:image/png;base64" in resp.data


def test_receipt_omits_qr_when_portal_revoked(client, staff_user, login, demo_client, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/portal/revoke", follow_redirects=True)
    resp = client.get(f"/orders/{order.id}/receipt")
    assert resp.status_code == 200
    assert b"data:image/png;base64" not in resp.data


def test_delete_garment_removes_lines_and_photos(client, staff_user, login, demo_client, sample_jpeg_bytes, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(
        f"/orders/{order.id}/garments/new",
        data={"garment_type": "trousers", "photo": (sample_jpeg_bytes, "test.jpg")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    garment = Garment.query.filter_by(order_id=order.id).first()
    garment_id = garment.id
    photo = GarmentPhoto.query.filter_by(garment_id=garment_id).first()
    photo_path = os.path.join(app.config["UPLOAD_FOLDER"], photo.filename)
    assert os.path.exists(photo_path)

    resp = client.post(f"/orders/{order.id}/garments/{garment_id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert db.session.get(Garment, garment_id) is None
    assert not os.path.exists(photo_path)


def test_garment_from_another_order_returns_404(client, staff_user, login, demo_client, app):
    order_a = _create_order(client, staff_user, login, demo_client)
    order_b = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order_a.id}/garments/new", data={"garment_type": "trousers"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order_a.id).first()

    resp = client.get(f"/orders/{order_b.id}/garments/{garment.id}/ticket")
    assert resp.status_code == 404


def test_edit_garment_updates_fields(client, staff_user, login, demo_client, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/garments/new", data={"garment_type": "trousers", "color": "Black"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order.id).first()

    resp = client.post(
        f"/orders/{order.id}/garments/{garment.id}/edit",
        data={"garment_type": "jacket", "color": "Navy", "brand": "Levi's"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    updated = db.session.get(Garment, garment.id)
    assert updated.garment_type == "jacket"
    assert updated.color == "Navy"
    assert updated.brand == "Levi's"


def test_delete_photo_removes_file_and_record(client, staff_user, login, demo_client, sample_jpeg_bytes, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(
        f"/orders/{order.id}/garments/new",
        data={"garment_type": "trousers", "photo": (sample_jpeg_bytes, "test.jpg")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    garment = Garment.query.filter_by(order_id=order.id).first()
    photo = GarmentPhoto.query.filter_by(garment_id=garment.id).first()
    photo_path = os.path.join(app.config["UPLOAD_FOLDER"], photo.filename)
    assert os.path.exists(photo_path)

    resp = client.post(
        f"/orders/{order.id}/garments/{garment.id}/photos/{photo.id}/delete", follow_redirects=True
    )
    assert resp.status_code == 200
    assert db.session.get(GarmentPhoto, photo.id) is None
    assert not os.path.exists(photo_path)


def test_edit_line_updates_fields(client, staff_user, login, demo_client, catalog_item, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/garments/new", data={"garment_type": "trousers"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order.id).first()
    client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines",
        data={"catalog_item_id": "", "description": "Original", "quantity": "1", "unit_price": "10.00", "vat_rate": "21"},
        follow_redirects=True,
    )
    line = OrderLine.query.filter_by(garment_id=garment.id).first()

    resp = client.get(f"/orders/{order.id}/garments/{garment.id}/lines/{line.id}/edit")
    assert resp.status_code == 200
    assert b"Original" in resp.data

    resp = client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines/{line.id}/edit",
        data={
            "catalog_item_id": str(catalog_item.id),
            "description": catalog_item.name,
            "quantity": "2",
            "unit_price": str(catalog_item.default_price),
            "vat_rate": str(catalog_item.default_vat_rate),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    updated = db.session.get(OrderLine, line.id)
    assert updated.description == catalog_item.name
    assert updated.quantity == 2
    assert updated.catalog_item_id == catalog_item.id


def test_delete_line_removes_it(client, staff_user, login, demo_client, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/garments/new", data={"garment_type": "trousers"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order.id).first()
    client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines",
        data={"catalog_item_id": "", "description": "To remove", "quantity": "1", "unit_price": "5.00", "vat_rate": "21"},
        follow_redirects=True,
    )
    line = OrderLine.query.filter_by(garment_id=garment.id).first()

    resp = client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines/{line.id}/delete", follow_redirects=True
    )
    assert resp.status_code == 200
    assert db.session.get(OrderLine, line.id) is None


def test_create_line_with_inventory_item_consumes_stock(client, staff_user, login, demo_client, inventory_item, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/garments/new", data={"garment_type": "dress"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order.id).first()

    resp = client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines",
        data={
            "inventory_item_id": str(inventory_item.id),
            "description": inventory_item.name,
            "quantity": "2",
            "unit_price": str(inventory_item.default_price),
            "vat_rate": str(inventory_item.default_vat_rate),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    line = OrderLine.query.filter_by(garment_id=garment.id).first()
    assert line.inventory_item_id == inventory_item.id

    updated_item = db.session.get(InventoryItem, inventory_item.id)
    assert updated_item.quantity_on_hand == Decimal("23.00")  # 25 - 2

    movement = StockMovement.query.filter_by(order_line_id=line.id).first()
    assert movement is not None
    assert movement.reason == "consumption"
    assert movement.quantity_delta == Decimal("-2.00")


def test_edit_line_quantity_change_adjusts_stock_delta(client, staff_user, login, demo_client, inventory_item, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/garments/new", data={"garment_type": "dress"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order.id).first()
    client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines",
        data={
            "inventory_item_id": str(inventory_item.id),
            "description": inventory_item.name,
            "quantity": "2",
            "unit_price": str(inventory_item.default_price),
            "vat_rate": str(inventory_item.default_vat_rate),
        },
        follow_redirects=True,
    )
    line = OrderLine.query.filter_by(garment_id=garment.id).first()

    resp = client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines/{line.id}/edit",
        data={
            "inventory_item_id": str(inventory_item.id),
            "description": inventory_item.name,
            "quantity": "5",
            "unit_price": str(inventory_item.default_price),
            "vat_rate": str(inventory_item.default_vat_rate),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    updated_item = db.session.get(InventoryItem, inventory_item.id)
    assert updated_item.quantity_on_hand == Decimal("20.00")  # 25 - 5


def test_edit_line_swap_inventory_item_restocks_old_and_consumes_new(
    client, staff_user, login, demo_client, inventory_item, app
):
    with app.app_context():
        other_item = InventoryItem(
            name="Trouser zipper 15cm — black",
            category="zippers",
            unit="pcs",
            default_price=Decimal("1.80"),
            default_vat_rate=Decimal("6.00"),
            quantity_on_hand=Decimal("30.00"),
            active=True,
        )
        db.session.add(other_item)
        db.session.commit()
        other_item_id = other_item.id

    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/garments/new", data={"garment_type": "dress"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order.id).first()
    client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines",
        data={
            "inventory_item_id": str(inventory_item.id),
            "description": inventory_item.name,
            "quantity": "1",
            "unit_price": str(inventory_item.default_price),
            "vat_rate": str(inventory_item.default_vat_rate),
        },
        follow_redirects=True,
    )
    line = OrderLine.query.filter_by(garment_id=garment.id).first()

    resp = client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines/{line.id}/edit",
        data={
            "inventory_item_id": str(other_item_id),
            "description": "Trouser zipper 15cm — black",
            "quantity": "1",
            "unit_price": "1.80",
            "vat_rate": "6",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        assert db.session.get(InventoryItem, inventory_item.id).quantity_on_hand == Decimal("25.00")  # restocked
        assert db.session.get(InventoryItem, other_item_id).quantity_on_hand == Decimal("29.00")  # consumed 1


def test_delete_line_restocks_inventory_item(client, staff_user, login, demo_client, inventory_item, app):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/garments/new", data={"garment_type": "dress"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order.id).first()
    client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines",
        data={
            "inventory_item_id": str(inventory_item.id),
            "description": inventory_item.name,
            "quantity": "3",
            "unit_price": str(inventory_item.default_price),
            "vat_rate": str(inventory_item.default_vat_rate),
        },
        follow_redirects=True,
    )
    line = OrderLine.query.filter_by(garment_id=garment.id).first()
    line_id = line.id
    assert db.session.get(InventoryItem, inventory_item.id).quantity_on_hand == Decimal("22.00")

    resp = client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines/{line_id}/delete", follow_redirects=True
    )
    assert resp.status_code == 200
    assert db.session.get(InventoryItem, inventory_item.id).quantity_on_hand == Decimal("25.00")

    # The original consumption movement survives the delete with its
    # quantity_delta/reason intact — only the dangling order_line_id is nulled.
    consumption = StockMovement.query.filter_by(reason="consumption", quantity_delta=Decimal("-3.00")).first()
    assert consumption is not None
    assert consumption.order_line_id is None


def test_order_line_cannot_reference_both_catalog_and_inventory_item(
    client, staff_user, login, demo_client, catalog_item, inventory_item, app
):
    order = _create_order(client, staff_user, login, demo_client)
    client.post(f"/orders/{order.id}/garments/new", data={"garment_type": "dress"}, follow_redirects=True)
    garment = Garment.query.filter_by(order_id=order.id).first()

    client.post(
        f"/orders/{order.id}/garments/{garment.id}/lines",
        data={
            "catalog_item_id": str(catalog_item.id),
            "inventory_item_id": str(inventory_item.id),
            "description": "Both set",
            "quantity": "1",
            "unit_price": "5.00",
            "vat_rate": "21",
        },
        follow_redirects=True,
    )
    assert OrderLine.query.filter_by(garment_id=garment.id).count() == 0
