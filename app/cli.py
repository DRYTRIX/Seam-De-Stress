import os
from datetime import date, timedelta
from decimal import Decimal

import click

from app.extensions import db
from app.models.catalog import ServiceCatalogItem
from app.models.client import Client
from app.models.inventory import InventoryItem
from app.models.invoice import Invoice, InvoiceLine
from app.models.order import Garment, Order, OrderLine, OrderStatusLog
from app.models.user import User
from app.seed_data import CATALOG_SEED, DEMO_CLIENTS, DEMO_ORDERS, INVENTORY_SEED


def register_cli(app):
    @app.cli.command("seed")
    def seed():
        """Create demo/admin data so the app is explorable immediately."""
        _ensure_admin_user()
        _ensure_catalog()
        _ensure_demo_inventory()
        _ensure_demo_clients()
        _ensure_demo_orders()
        _ensure_demo_invoice()
        click.echo("Seed complete.")


def _ensure_admin_user():
    username = os.environ.get("ADMIN_USERNAME", "admin")
    existing = User.query.filter_by(username=username).first()
    if existing:
        click.echo(f"Admin user '{username}' already exists, skipping.")
        return

    user = User(
        username=username,
        email=os.environ.get("ADMIN_EMAIL", "admin@example.com"),
        full_name=os.environ.get("ADMIN_FULL_NAME", "Shop Owner"),
        role="admin",
        preferred_language="nl",
    )
    user.set_password(os.environ.get("ADMIN_PASSWORD", "changeme123"))
    db.session.add(user)
    db.session.commit()
    click.echo(f"Created admin user '{username}'.")


def _ensure_catalog():
    if ServiceCatalogItem.query.first():
        click.echo("Service catalog already has items, skipping.")
        return

    for name, category, description, price, vat_rate, minutes in CATALOG_SEED:
        db.session.add(
            ServiceCatalogItem(
                name=name,
                category=category,
                description=description,
                default_price=Decimal(price),
                default_vat_rate=Decimal(vat_rate),
                estimated_minutes=minutes,
                active=True,
            )
        )
    db.session.commit()
    click.echo(f"Seeded {len(CATALOG_SEED)} service catalog items.")


def _ensure_demo_inventory():
    if InventoryItem.query.first():
        click.echo("Inventory already has items, skipping.")
        return

    for name, sku, category, description, unit, price, vat_rate, qty, threshold in INVENTORY_SEED:
        db.session.add(
            InventoryItem(
                name=name,
                sku=sku,
                category=category,
                description=description,
                unit=unit,
                default_price=Decimal(price),
                default_vat_rate=Decimal(vat_rate),
                quantity_on_hand=Decimal(qty),
                low_stock_threshold=Decimal(threshold),
                active=True,
            )
        )
    db.session.commit()
    click.echo(f"Seeded {len(INVENTORY_SEED)} inventory items.")


def _ensure_demo_clients():
    if Client.query.first():
        click.echo("Clients already exist, skipping.")
        return

    for name, phone, email, language, notes, consent in DEMO_CLIENTS:
        db.session.add(
            Client(
                name=name,
                phone=phone,
                email=email,
                preferred_language=language,
                notes=notes,
                consent_notifications=consent,
            )
        )
    db.session.commit()
    click.echo(f"Seeded {len(DEMO_CLIENTS)} demo clients.")


def _ensure_demo_orders():
    if Order.query.first():
        click.echo("Orders already exist, skipping.")
        return

    clients_by_name = {c.name: c for c in Client.query.all()}
    catalog_by_name = {i.name: i for i in ServiceCatalogItem.query.all()}
    inventory_by_name = {i.name: i for i in InventoryItem.query.all()}
    admin = User.query.filter_by(role="admin").first()

    for spec in DEMO_ORDERS:
        client = clients_by_name.get(spec["client"])
        if client is None:
            continue

        order = Order(
            client_id=client.id,
            promised_date=date.today() + timedelta(days=spec["promised_offset_days"]),
            status=spec["status"],
            payment_status=spec["payment_status"],
            express=spec["express"],
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(
            OrderStatusLog(order_id=order.id, user_id=admin.id if admin else None, from_status=None, to_status=order.status)
        )

        for garment_spec in spec["garments"]:
            garment = Garment(
                order_id=order.id,
                garment_type=garment_spec["type"],
                color=garment_spec["color"],
                brand=garment_spec["brand"],
            )
            db.session.add(garment)
            db.session.flush()

            for line_spec in garment_spec["lines"]:
                if isinstance(line_spec, tuple) and line_spec[0] == "inventory":
                    inventory_item = inventory_by_name.get(line_spec[1])
                    if inventory_item is None:
                        continue
                    # A one-shot bootstrap script, not a request through
                    # orders.create_line — intentionally skips the
                    # quantity_on_hand/StockMovement side effect that route
                    # applies.
                    db.session.add(
                        OrderLine(
                            garment_id=garment.id,
                            inventory_item_id=inventory_item.id,
                            description=inventory_item.name,
                            quantity=1,
                            unit_price=inventory_item.default_price,
                            vat_rate=inventory_item.default_vat_rate,
                        )
                    )
                    continue

                catalog_item = catalog_by_name.get(line_spec)
                if catalog_item is None:
                    continue
                db.session.add(
                    OrderLine(
                        garment_id=garment.id,
                        catalog_item_id=catalog_item.id,
                        description=catalog_item.name,
                        quantity=1,
                        unit_price=catalog_item.default_price,
                        vat_rate=catalog_item.default_vat_rate,
                    )
                )

    db.session.commit()
    click.echo(f"Seeded {len(DEMO_ORDERS)} demo orders.")


def _ensure_demo_invoice():
    if Invoice.query.first():
        click.echo("Invoices already exist, skipping.")
        return

    order = Order.query.filter_by(status="picked_up", payment_status="paid", invoice_id=None).first()
    if order is None:
        click.echo("No picked-up/paid order available to invoice, skipping.")
        return

    invoice = Invoice(
        invoice_number=Invoice.generate_number(date.today().year),
        client_id=order.client_id,
        due_date=date.today() + timedelta(days=30),
        status="paid",
    )
    db.session.add(invoice)
    db.session.flush()
    order.invoice_id = invoice.id
    for garment in order.garments:
        for line in garment.lines:
            db.session.add(
                InvoiceLine(
                    invoice_id=invoice.id,
                    description=f"{order.code} — {line.description}",
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    vat_rate=line.vat_rate,
                )
            )
    db.session.commit()
    click.echo(f"Seeded demo invoice {invoice.invoice_number}.")
