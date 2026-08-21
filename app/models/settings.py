from decimal import Decimal

from app.extensions import db
from app.models.mixins import TimestampMixin

DEFAULT_DAILY_CAPACITY_MINUTES = 240
DEFAULT_LOW_STOCK_THRESHOLD = Decimal("5.00")


class Settings(TimestampMixin, db.Model):
    """Single-row shop configuration. Grows with later milestones
    (notification-template editing) — invoicing/branding basics now cover
    what the client portal and invoice PDFs need."""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    daily_capacity_minutes = db.Column(db.Integer, nullable=False, default=DEFAULT_DAILY_CAPACITY_MINUTES)

    company_name = db.Column(db.String(128), nullable=True)
    company_address = db.Column(db.Text, nullable=True)
    company_phone = db.Column(db.String(32), nullable=True)
    opening_hours = db.Column(db.Text, nullable=True)
    portal_show_prices = db.Column(db.Boolean, nullable=False, default=True)

    company_vat_number = db.Column(db.String(32), nullable=True)
    company_iban = db.Column(db.String(48), nullable=True)
    logo_filename = db.Column(db.String(255), nullable=True)

    default_low_stock_threshold = db.Column(
        db.Numeric(10, 2), nullable=False, default=DEFAULT_LOW_STOCK_THRESHOLD
    )

    @classmethod
    def get_solo(cls):
        settings = db.session.get(cls, 1)
        if settings is None:
            settings = cls(
                id=1,
                daily_capacity_minutes=DEFAULT_DAILY_CAPACITY_MINUTES,
                default_low_stock_threshold=DEFAULT_LOW_STOCK_THRESHOLD,
            )
            db.session.add(settings)
            db.session.commit()
        return settings

    def __repr__(self):
        return f"<Settings daily_capacity_minutes={self.daily_capacity_minutes}>"
