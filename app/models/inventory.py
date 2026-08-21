from app.extensions import db
from app.models.mixins import TimestampMixin


class InventoryItem(TimestampMixin, db.Model):
    __tablename__ = "inventory_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    sku = db.Column(db.String(64), nullable=True)
    category = db.Column(db.String(32), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    unit = db.Column(db.String(16), nullable=False, default="pcs")
    default_price = db.Column(db.Numeric(8, 2), nullable=False)
    default_vat_rate = db.Column(db.Numeric(5, 2), nullable=False, default=21)
    quantity_on_hand = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    low_stock_threshold = db.Column(db.Numeric(10, 2), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    @property
    def effective_low_stock_threshold(self):
        if self.low_stock_threshold is not None:
            return self.low_stock_threshold
        from app.models.settings import Settings

        return Settings.get_solo().default_low_stock_threshold

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.effective_low_stock_threshold

    def __repr__(self):
        return f"<InventoryItem {self.name}>"


class StockMovement(TimestampMixin, db.Model):
    """Append-only audit log of stock changes — mirrors OrderStatusLog: one row
    per event, never mutated after write. order_line_id is nullable with
    ondelete="SET NULL" so deleting an OrderLine can never fail or rewrite
    history — only the dangling reference is cleared, quantity_delta/reason/
    note stay intact."""

    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)
    inventory_item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_items.id"), nullable=False, index=True
    )
    order_line_id = db.Column(
        db.Integer, db.ForeignKey("order_lines.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quantity_delta = db.Column(db.Numeric(10, 2), nullable=False)
    reason = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    inventory_item = db.relationship(
        "InventoryItem",
        backref=db.backref("movements", order_by="StockMovement.created_at.desc()", cascade="all, delete-orphan"),
    )
    order_line = db.relationship("OrderLine", passive_deletes=True)
    created_by = db.relationship("User")

    def __repr__(self):
        return f"<StockMovement {self.reason} {self.quantity_delta}>"
