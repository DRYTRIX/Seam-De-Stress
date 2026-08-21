from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models.mixins import TimestampMixin


class Invoice(TimestampMixin, db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)
    issue_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="draft")
    notes = db.Column(db.Text, nullable=True)

    client = db.relationship("Client", backref=db.backref("invoices", order_by="Invoice.issue_date.desc()"))
    lines = db.relationship(
        "InvoiceLine", backref="invoice", cascade="all, delete-orphan", order_by="InvoiceLine.id"
    )

    @classmethod
    def generate_number(cls, year):
        """Sequential per year, e.g. 2026-0001. Single-writer assumption: fine
        for one shop's invoicing volume; a genuine concurrent create would hit
        the unique constraint rather than silently duplicate a number."""
        prefix = f"{year}-"
        latest = (
            cls.query.filter(cls.invoice_number.like(f"{prefix}%"))
            .order_by(cls.invoice_number.desc())
            .first()
        )
        seq = int(latest.invoice_number.split("-")[1]) + 1 if latest else 1
        return f"{prefix}{seq:04d}"

    @property
    def subtotal(self):
        return sum((line.line_total for line in self.lines), Decimal("0.00"))

    @property
    def vat_total(self):
        return sum((line.vat_amount for line in self.lines), Decimal("0.00"))

    @property
    def total(self):
        return self.subtotal + self.vat_total

    @property
    def vat_breakdown(self):
        """{vat_rate: {"subtotal": Decimal, "vat_amount": Decimal}}, sorted by rate."""
        breakdown = defaultdict(lambda: {"subtotal": Decimal("0.00"), "vat_amount": Decimal("0.00")})
        for line in self.lines:
            entry = breakdown[line.vat_rate]
            entry["subtotal"] += line.line_total
            entry["vat_amount"] += line.vat_amount
        return dict(sorted(breakdown.items()))

    def __repr__(self):
        return f"<Invoice {self.invoice_number}>"


class InvoiceLine(TimestampMixin, db.Model):
    """A snapshot of an OrderLine at invoicing time — deliberately copied, not
    referenced live, so later edits to an order or catalog price can't alter
    an already-issued invoice."""

    __tablename__ = "invoice_lines"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(8, 2), nullable=False)
    vat_rate = db.Column(db.Numeric(5, 2), nullable=False, default=21)

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
        return f"<InvoiceLine {self.description!r}>"
