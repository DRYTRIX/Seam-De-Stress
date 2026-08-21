from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models.invoice import Invoice, InvoiceLine
from app.models.order import Garment, Order, OrderLine


def _make_invoiceable_order_with_inventory_line(client_id, inventory_item, status="picked_up"):
    order = Order(client_id=client_id, status=status, payment_status="paid")
    db.session.add(order)
    db.session.flush()
    garment = Garment(order_id=order.id, garment_type="dress")
    db.session.add(garment)
    db.session.flush()
    db.session.add(
        OrderLine(
            garment_id=garment.id,
            inventory_item_id=inventory_item.id,
            description=inventory_item.name,
            quantity=2,
            unit_price=inventory_item.default_price,
            vat_rate=inventory_item.default_vat_rate,
        )
    )
    db.session.commit()
    return order


def _make_invoiceable_order(client_id, status="picked_up"):
    order = Order(client_id=client_id, status=status, payment_status="paid")
    db.session.add(order)
    db.session.flush()
    garment = Garment(order_id=order.id, garment_type="trousers")
    db.session.add(garment)
    db.session.flush()
    db.session.add(
        OrderLine(
            garment_id=garment.id,
            description="Trouser hem",
            quantity=1,
            unit_price=Decimal("12.00"),
            vat_rate=Decimal("21.00"),
        )
    )
    db.session.commit()
    return order


def test_generate_number_is_sequential_per_year(app, demo_client):
    first = Invoice(invoice_number=Invoice.generate_number(2026), client_id=demo_client.id)
    db.session.add(first)
    db.session.commit()
    assert first.invoice_number == "2026-0001"

    second = Invoice(invoice_number=Invoice.generate_number(2026), client_id=demo_client.id)
    db.session.add(second)
    db.session.commit()
    assert second.invoice_number == "2026-0002"

    # different year restarts the sequence
    assert Invoice.generate_number(2027) == "2027-0001"


def test_invoice_totals_and_vat_breakdown(app, demo_client):
    invoice = Invoice(invoice_number="2026-0099", client_id=demo_client.id)
    db.session.add(invoice)
    db.session.flush()
    db.session.add_all(
        [
            InvoiceLine(invoice_id=invoice.id, description="A", quantity=1, unit_price=Decimal("12.00"), vat_rate=Decimal("21.00")),
            InvoiceLine(invoice_id=invoice.id, description="B", quantity=2, unit_price=Decimal("5.00"), vat_rate=Decimal("6.00")),
        ]
    )
    db.session.commit()

    assert invoice.subtotal == Decimal("22.00")
    assert invoice.vat_total == Decimal("2.52") + Decimal("0.60")
    assert invoice.total == invoice.subtotal + invoice.vat_total

    breakdown = invoice.vat_breakdown
    assert breakdown[Decimal("21.00")]["subtotal"] == Decimal("12.00")
    assert breakdown[Decimal("6.00")]["subtotal"] == Decimal("10.00")


def test_invoices_require_admin(client, staff_user, login):
    resp = client.get("/invoices/", follow_redirects=False)
    assert resp.status_code == 302  # anonymous -> login

    login(staff_user)
    resp = client.get("/invoices/")
    assert resp.status_code == 403


def test_create_invoice_from_order_copies_lines_and_links_order(client, admin_user, login, demo_client, app):
    login(admin_user)
    order = _make_invoiceable_order(demo_client.id)

    resp = client.get(f"/invoices/new?client_id={demo_client.id}")
    assert resp.status_code == 200
    assert order.code.encode() in resp.data

    resp = client.post(
        "/invoices/new",
        data={"client_id": demo_client.id, "order_ids": str(order.id), "due_date": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    updated_order = db.session.get(Order, order.id)
    assert updated_order.invoice_id is not None

    invoice = db.session.get(Invoice, updated_order.invoice_id)
    assert invoice.invoice_number == f"{date.today().year}-0001"
    assert len(invoice.lines) == 1
    assert invoice.lines[0].description.startswith(order.code)
    assert invoice.total == Decimal("14.52")


def test_create_invoice_from_order_with_inventory_line_copies_snapshot(
    client, admin_user, login, demo_client, inventory_item, app
):
    login(admin_user)
    order = _make_invoiceable_order_with_inventory_line(demo_client.id, inventory_item)

    resp = client.post(
        "/invoices/new",
        data={"client_id": demo_client.id, "order_ids": str(order.id), "due_date": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    updated_order = db.session.get(Order, order.id)
    invoice = db.session.get(Invoice, updated_order.invoice_id)
    assert len(invoice.lines) == 1
    line = invoice.lines[0]
    assert line.description == f"{order.code} — {inventory_item.name}"
    assert line.quantity == 2
    assert line.unit_price == inventory_item.default_price
    assert line.vat_rate == inventory_item.default_vat_rate


def test_already_invoiced_order_is_not_offered_again(client, admin_user, login, demo_client, app):
    login(admin_user)
    order = _make_invoiceable_order(demo_client.id)
    client.post(
        "/invoices/new",
        data={"client_id": demo_client.id, "order_ids": str(order.id), "due_date": ""},
        follow_redirects=True,
    )

    resp = client.get(f"/invoices/new?client_id={demo_client.id}")
    assert b"No uninvoiced orders" in resp.data


def test_cancelled_orders_are_not_eligible(client, admin_user, login, demo_client, app):
    login(admin_user)
    order = _make_invoiceable_order(demo_client.id, status="cancelled")

    resp = client.get(f"/invoices/new?client_id={demo_client.id}")
    assert order.code.encode() not in resp.data


def test_update_invoice_status(client, admin_user, login, demo_client, app):
    login(admin_user)
    invoice = Invoice(invoice_number="2026-0050", client_id=demo_client.id)
    db.session.add(invoice)
    db.session.commit()

    resp = client.post(f"/invoices/{invoice.id}/status", data={"status": "sent"}, follow_redirects=True)
    assert resp.status_code == 200
    assert db.session.get(Invoice, invoice.id).status == "sent"

    resp = client.post(f"/invoices/{invoice.id}/status", data={"status": "not-a-status"})
    assert resp.status_code == 400


def test_invoice_pdf_returns_a_real_pdf(client, admin_user, login, demo_client, app):
    login(admin_user)
    invoice = Invoice(invoice_number="2026-0051", client_id=demo_client.id)
    db.session.add(invoice)
    db.session.flush()
    db.session.add(
        InvoiceLine(invoice_id=invoice.id, description="Test line", quantity=1, unit_price=Decimal("10.00"), vat_rate=Decimal("21.00"))
    )
    db.session.commit()

    resp = client.get(f"/invoices/{invoice.id}/pdf")
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"
    assert resp.data[:4] == b"%PDF"


def test_invoice_csv_export(client, admin_user, login, demo_client, app):
    login(admin_user)
    invoice = Invoice(invoice_number="2026-0052", client_id=demo_client.id)
    db.session.add(invoice)
    db.session.commit()

    resp = client.get("/invoices/export.csv")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/csv")
    assert b"2026-0052" in resp.data


def test_invoice_list_filters_by_status_and_search(client, admin_user, login, demo_client, app):
    login(admin_user)
    from app.models.client import Client

    other_client = Client(name="Marie Lefebvre", preferred_language="fr")
    db.session.add(other_client)
    db.session.flush()

    draft = Invoice(invoice_number="2026-0060", client_id=demo_client.id, status="draft")
    paid = Invoice(invoice_number="2026-0061", client_id=other_client.id, status="paid")
    db.session.add_all([draft, paid])
    db.session.commit()

    resp = client.get("/invoices/?status=paid")
    assert b"2026-0061" in resp.data
    assert b"2026-0060" not in resp.data

    resp = client.get("/invoices/?q=Marie")
    assert b"2026-0061" in resp.data
    assert b"2026-0060" not in resp.data

    resp = client.get("/invoices/?q=2026-0060")
    assert b"2026-0060" in resp.data
    assert b"2026-0061" not in resp.data


def test_settings_logo_upload_and_pdf_embed(client, admin_user, login, app):
    import io

    from PIL import Image

    login(admin_user)
    buf = io.BytesIO()
    Image.new("RGBA", (200, 150), color=(10, 20, 30, 255)).save(buf, format="PNG")
    buf.seek(0)

    resp = client.post(
        "/settings/",
        data={
            "daily_capacity_minutes": "240",
            "default_low_stock_threshold": "5",
            "portal_show_prices": "y",
            "logo": (buf, "logo.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200

    from app.models.settings import Settings

    settings = Settings.get_solo()
    assert settings.logo_filename == "branding/logo.png"

    import os

    assert os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], settings.logo_filename))
