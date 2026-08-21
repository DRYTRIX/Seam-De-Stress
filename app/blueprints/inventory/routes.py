from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.blueprints.inventory.forms import InventoryItemForm, StockAdjustForm, StockReceiveForm
from app.constants import INVENTORY_CATEGORIES, ROLE_ADMIN, STOCK_MOVEMENT_REASON_RECEIVED
from app.extensions import db
from app.models.inventory import InventoryItem
from app.services.inventory import record_movement
from app.utils.decorators import roles_required

bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@bp.route("/")
@login_required
def list_items():
    category = request.args.get("category", "")
    low_only = request.args.get("low_stock") == "1"
    query = InventoryItem.query
    if category:
        query = query.filter_by(category=category)
    items = query.order_by(InventoryItem.category, InventoryItem.name).all()
    if low_only:
        items = [i for i in items if i.is_low_stock]
    return render_template(
        "inventory/list.html",
        items=items,
        categories=INVENTORY_CATEGORIES,
        selected_category=category,
        low_only=low_only,
    )


@bp.route("/new", methods=["GET", "POST"])
@roles_required(ROLE_ADMIN)
def create():
    form = InventoryItemForm()
    if form.validate_on_submit():
        item = InventoryItem()
        form.populate_obj(item)
        db.session.add(item)
        db.session.commit()
        flash(f"Material “{item.name}” created.", "success")
        return redirect(url_for("inventory.list_items"))
    return render_template("inventory/form.html", form=form, item=None)


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@roles_required(ROLE_ADMIN)
def edit(item_id):
    item = db.get_or_404(InventoryItem, item_id)
    form = InventoryItemForm(obj=item)
    if form.validate_on_submit():
        form.populate_obj(item)  # quantity_on_hand untouched: not a form field
        db.session.commit()
        flash(f"Material “{item.name}” updated.", "success")
        return redirect(url_for("inventory.list_items"))
    return render_template("inventory/form.html", form=form, item=item)


@bp.route("/<int:item_id>/toggle-active", methods=["POST"])
@roles_required(ROLE_ADMIN)
def toggle_active(item_id):
    item = db.get_or_404(InventoryItem, item_id)
    item.active = not item.active
    db.session.commit()
    flash(f"“{item.name}” is now {'active' if item.active else 'inactive'}.", "info")
    return redirect(url_for("inventory.list_items", category=request.form.get("category", "")))


@bp.route("/<int:item_id>")
@login_required
def view(item_id):
    item = db.get_or_404(InventoryItem, item_id)
    return render_template(
        "inventory/view.html",
        item=item,
        movements=item.movements,
        receive_form=StockReceiveForm(),
        adjust_form=StockAdjustForm(),
    )


@bp.route("/<int:item_id>/receive", methods=["POST"])
@roles_required(ROLE_ADMIN)
def receive(item_id):
    item = db.get_or_404(InventoryItem, item_id)
    form = StockReceiveForm()
    if form.validate_on_submit():
        record_movement(
            item, form.quantity.data, STOCK_MOVEMENT_REASON_RECEIVED, current_user, note=form.note.data
        )
        db.session.commit()
        flash(f"Received {form.quantity.data} {item.unit} of “{item.name}”.", "success")
    else:
        for _field_name, errors in form.errors.items():
            for error in errors:
                flash(error, "danger")
    return redirect(url_for("inventory.view", item_id=item.id))


@bp.route("/<int:item_id>/adjust", methods=["POST"])
@roles_required(ROLE_ADMIN)
def adjust(item_id):
    item = db.get_or_404(InventoryItem, item_id)
    form = StockAdjustForm()
    if form.validate_on_submit():
        record_movement(item, form.quantity_delta.data, form.reason.data, current_user, note=form.note.data)
        db.session.commit()
        if item.quantity_on_hand < 0:
            flash(
                f"Warning: “{item.name}” stock is now negative ({item.quantity_on_hand} {item.unit}).",
                "warning",
            )
        flash(f"Stock adjusted for “{item.name}”.", "info")
    else:
        for _field_name, errors in form.errors.items():
            for error in errors:
                flash(error, "danger")
    return redirect(url_for("inventory.view", item_id=item.id))
