from app.extensions import db
from app.models.mixins import TimestampMixin


class ServiceCatalogItem(TimestampMixin, db.Model):
    __tablename__ = "service_catalog_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(32), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    default_price = db.Column(db.Numeric(8, 2), nullable=False)
    default_vat_rate = db.Column(db.Numeric(5, 2), nullable=False, default=21)
    estimated_minutes = db.Column(db.Integer, nullable=False, default=15)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<ServiceCatalogItem {self.name}>"
