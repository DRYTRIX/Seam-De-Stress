from decimal import Decimal

from app.constants import STOCK_MOVEMENT_REASON_CONSUMPTION
from app.extensions import db
from app.models.inventory import InventoryItem, StockMovement


def record_movement(item, quantity_delta, reason, user, order_line_id=None, note=None):
    """Apply a signed quantity_delta to item.quantity_on_hand and append an
    audit-log StockMovement row (never mutated after write). Does not clamp
    at zero — negative on-hand stock is allowed; callers decide whether to
    warn. Caller is responsible for db.session.commit()."""
    delta = Decimal(str(quantity_delta))
    item.quantity_on_hand = item.quantity_on_hand + delta
    movement = StockMovement(
        inventory_item_id=item.id,
        order_line_id=order_line_id,
        quantity_delta=delta,
        reason=reason,
        note=note,
        created_by_id=user.id if user else None,
    )
    db.session.add(movement)
    return movement


def sync_order_line_stock(*, old_item_id, old_quantity, new_item_id, new_quantity, order_line, user):
    """Reconciles quantity_on_hand + StockMovement rows when an order line's
    inventory_item_id/quantity changes. Covers all three call sites:
      - create_line: old_item_id=None, old_quantity=0
      - edit_line:    both old_* and new_* populated from before/after the edit
      - delete_line:  new_item_id=None, new_quantity=0
    Returns the InventoryItem rows touched, so the caller can flash a warning
    for any that end up negative."""
    touched = []
    if old_item_id == new_item_id:
        if new_item_id is not None and old_quantity != new_quantity:
            item = db.session.get(InventoryItem, new_item_id)
            delta = Decimal(str(old_quantity)) - Decimal(str(new_quantity))
            record_movement(item, delta, STOCK_MOVEMENT_REASON_CONSUMPTION, user, order_line_id=order_line.id)
            touched.append(item)
    else:
        if old_item_id is not None:
            old_item = db.session.get(InventoryItem, old_item_id)
            record_movement(
                old_item,
                old_quantity,
                STOCK_MOVEMENT_REASON_CONSUMPTION,
                user,
                order_line_id=order_line.id,
                note="Line no longer uses this material",
            )
            touched.append(old_item)
        if new_item_id is not None:
            new_item = db.session.get(InventoryItem, new_item_id)
            record_movement(
                new_item, -Decimal(str(new_quantity)), STOCK_MOVEMENT_REASON_CONSUMPTION, user, order_line_id=order_line.id
            )
            touched.append(new_item)
    return touched
