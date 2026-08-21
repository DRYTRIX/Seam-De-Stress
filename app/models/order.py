import secrets
from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models.mixins import TimestampMixin


def generate_portal_token():
    return secrets.token_urlsafe(32)


class Order(TimestampMixin, db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)
    intake_date = db.Column(db.Date, nullable=False, default=date.today)
    promised_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="received", index=True)
    payment_status = db.Column(db.String(20), nullable=False, default="unpaid")
    express = db.Column(db.Boolean, nullable=False, default=False)
    internal_notes = db.Column(db.Text, nullable=True)

    # Nullable at the DB level on purpose: rows created before this column
    # existed keep NULL until someone explicitly generates a link for them
    # (see orders.regenerate_portal); every new order gets one automatically.
    portal_token = db.Column(db.String(64), unique=True, nullable=True, index=True, default=generate_portal_token)
    portal_revoked = db.Column(db.Boolean, nullable=False, default=False)

    # Set once an order is folded into an invoice; orders don't get invoiced twice.
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=True, index=True)

    client = db.relationship("Client", backref=db.backref("orders", order_by="Order.intake_date.desc()"))
    garments = db.relationship(
        "Garment", backref="order", cascade="all, delete-orphan", order_by="Garment.id"
    )
    status_logs = db.relationship(
        "OrderStatusLog",
        backref="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusLog.created_at",
    )
    notifications = db.relationship(
        "NotificationLog",
        backref="order",
        cascade="all, delete-orphan",
        order_by="NotificationLog.created_at.desc()",
    )
    invoice = db.relationship("Invoice", backref=db.backref("orders", order_by="Order.id"))

    @property
    def portal_active(self):
        return bool(self.portal_token) and not self.portal_revoked

    @property
    def code(self):
        return f"SDS-{self.id:05d}"

    @property
    def subtotal(self):
        return sum((line.line_total for g in self.garments for line in g.lines), Decimal("0.00"))

    @property
    def vat_total(self):
        return sum((line.vat_amount for g in self.garments for line in g.lines), Decimal("0.00"))

    @property
    def total(self):
        return self.subtotal + self.vat_total

    @property
    def total_estimated_minutes(self):
        return sum(
            (line.catalog_item.estimated_minutes if line.catalog_item else 0)
            for g in self.garments
            for line in g.lines
        )

    @property
    def is_overdue(self):
        return (
            self.promised_date is not None
            and self.promised_date < date.today()
            and self.status not in ("picked_up", "cancelled")
        )

    def __repr__(self):
        return f"<Order {self.code}>"


class Garment(TimestampMixin, db.Model):
    __tablename__ = "garments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    garment_type = db.Column(db.String(20), nullable=False, default="other")
    color = db.Column(db.String(64), nullable=True)
    brand = db.Column(db.String(64), nullable=True)
    description = db.Column(db.Text, nullable=True)
    measurements_notes = db.Column(db.Text, nullable=True)

    lines = db.relationship(
        "OrderLine", backref="garment", cascade="all, delete-orphan", order_by="OrderLine.id"
    )
    photos = db.relationship(
        "GarmentPhoto", backref="garment", cascade="all, delete-orphan", order_by="GarmentPhoto.id"
    )

    @property
    def subtotal(self):
        return sum((line.line_total for line in self.lines), Decimal("0.00"))

    def __repr__(self):
        return f"<Garment {self.garment_type} #{self.id}>"


class OrderLine(TimestampMixin, db.Model):
    __tablename__ = "order_lines"

    id = db.Column(db.Integer, primary_key=True)
    garment_id = db.Column(db.Integer, db.ForeignKey("garments.id"), nullable=False, index=True)
    catalog_item_id = db.Column(
        db.Integer, db.ForeignKey("service_catalog_items.id"), nullable=True
    )
    inventory_item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_items.id"), nullable=True
    )
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(8, 2), nullable=False)
    vat_rate = db.Column(db.Numeric(5, 2), nullable=False, default=21)
    notes = db.Column(db.Text, nullable=True)

    catalog_item = db.relationship("ServiceCatalogItem")
    inventory_item = db.relationship("InventoryItem")

    @property
    def line_total(self):
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))

    @property
    def vat_amount(self):
        return (self.line_total * self.vat_rate / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def line_total_with_vat(self):
        return self.line_total + self.vat_amount

    def __repr__(self):
        return f"<OrderLine {self.description!r}>"


class GarmentPhoto(TimestampMixin, db.Model):
    __tablename__ = "garment_photos"

    id = db.Column(db.Integer, primary_key=True)
    garment_id = db.Column(db.Integer, db.ForeignKey("garments.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    thumbnail_filename = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<GarmentPhoto {self.filename}>"


class OrderStatusLog(TimestampMixin, db.Model):
    __tablename__ = "order_status_logs"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    from_status = db.Column(db.String(20), nullable=True)
    to_status = db.Column(db.String(20), nullable=False)

    user = db.relationship("User")

    def __repr__(self):
        return f"<OrderStatusLog {self.from_status} -> {self.to_status}>"


class NotificationLog(TimestampMixin, db.Model):
    __tablename__ = "notification_logs"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    channel = db.Column(db.String(20), nullable=False, default="email")
    template_key = db.Column(db.String(50), nullable=False)
    recipient = db.Column(db.String(255), nullable=True)
    language = db.Column(db.String(5), nullable=True)
    status = db.Column(db.String(20), nullable=False)
    error_message = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<NotificationLog {self.channel}:{self.template_key} {self.status}>"
