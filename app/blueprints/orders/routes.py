from datetime import date

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from app.blueprints.orders.forms import GarmentForm, OrderForm, OrderLineForm
from app.constants import ORDER_STATUSES, PAYMENT_STATUSES, next_order_status
from app.extensions import db
from app.models.catalog import ServiceCatalogItem
from app.models.client import Client
from app.models.inventory import InventoryItem
from app.models.order import (
    Garment,
    GarmentPhoto,
    Order,
    OrderLine,
    OrderStatusLog,
    generate_portal_token,
)
from app.models.settings import Settings
from app.services.inventory import sync_order_line_stock
from app.services.notifications import notify_order_ready
from app.services.planning import get_daily_loads
from app.utils.qr import qr_data_uri
from app.utils.uploads import allowed_file, delete_garment_photo_files, save_garment_photo

bp = Blueprint("orders", __name__, url_prefix="/orders")


def _populate_client_choices(form, preselected_id=None):
    clients = Client.query.order_by(Client.name).all()
    form.client_id.choices = [(c.id, f"{c.name} — {c.phone}" if c.phone else c.name) for c in clients]
    if preselected_id is not None and request.method == "GET":
        form.client_id.data = preselected_id


def _populate_catalog_choices(form):
    """Active catalog items, grouped by category and ordered most-used first within it."""
    usage_counts = dict(
        db.session.query(OrderLine.catalog_item_id, func.count(OrderLine.id))
        .group_by(OrderLine.catalog_item_id)
        .all()
    )
    items = ServiceCatalogItem.query.filter_by(active=True).all()
    items.sort(key=lambda i: (i.category, -usage_counts.get(i.id, 0), i.name))
    form.catalog_item_id.choices = [("", "— Custom line —")] + [(item.id, item.name) for item in items]
    return items


def _populate_inventory_choices(form):
    """Active inventory items, grouped by category and ordered most-used first within it."""
    usage_counts = dict(
        db.session.query(OrderLine.inventory_item_id, func.count(OrderLine.id))
        .group_by(OrderLine.inventory_item_id)
        .all()
    )
    items = InventoryItem.query.filter_by(active=True).all()
    items.sort(key=lambda i: (i.category, -usage_counts.get(i.id, 0), i.name))
    form.inventory_item_id.choices = [("", "— Custom line —")] + [(item.id, item.name) for item in items]
    return items


def _parse_order_code(q):
    cleaned = q.strip().upper().replace("SDS-", "").replace("SDS", "")
    try:
        return int(cleaned)
    except ValueError:
        return None


def _get_order_garment(order_id, garment_id):
    order = db.get_or_404(Order, order_id)
    garment = db.get_or_404(Garment, garment_id)
    if garment.order_id != order.id:
        abort(404)
    return order, garment


@bp.route("/")
@login_required
def list_orders():
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    query = Order.query.join(Client)
    if status:
        query = query.filter(Order.status == status)
    if q:
        order_id = _parse_order_code(q)
        if order_id is not None:
            query = query.filter(Order.id == order_id)
        else:
            query = query.filter(Client.name.ilike(f"%{q}%"))
    orders = query.order_by(Order.intake_date.desc(), Order.id.desc()).all()
    return render_template("orders/list.html", orders=orders, status=status, q=q, statuses=ORDER_STATUSES)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = OrderForm()
    _populate_client_choices(form, preselected_id=request.args.get("client_id", type=int))

    if form.validate_on_submit():
        order = Order(
            client_id=form.client_id.data,
            promised_date=form.promised_date.data,
            express=form.express.data,
            internal_notes=form.internal_notes.data,
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(
            OrderStatusLog(order_id=order.id, user_id=current_user.id, from_status=None, to_status=order.status)
        )
        db.session.commit()
        flash(f"Order {order.code} created — add garments below.", "success")
        return redirect(url_for("orders.view", order_id=order.id))

    settings = Settings.get_solo()
    upcoming_loads = get_daily_loads(date.today(), 14, settings.daily_capacity_minutes)
    return render_template("orders/form.html", form=form, upcoming_loads=upcoming_loads)


@bp.route("/<int:order_id>")
@login_required
def view(order_id):
    order = db.get_or_404(Order, order_id)
    garment_form = GarmentForm()
    line_form = OrderLineForm()
    catalog_items = _populate_catalog_choices(line_form)
    inventory_items = _populate_inventory_choices(line_form)
    return render_template(
        "orders/view.html",
        order=order,
        garment_form=garment_form,
        line_form=line_form,
        catalog_items=catalog_items,
        inventory_items=inventory_items,
        next_status=next_order_status(order.status),
    )


@bp.route("/<int:order_id>/status", methods=["POST"])
@login_required
def update_status(order_id):
    order = db.get_or_404(Order, order_id)
    new_status = request.form.get("status")
    if new_status not in dict(ORDER_STATUSES):
        abort(400)
    if new_status != order.status:
        db.session.add(
            OrderStatusLog(order_id=order.id, user_id=current_user.id, from_status=order.status, to_status=new_status)
        )
        order.status = new_status
        db.session.commit()
        flash(f"Order {order.code} marked as {dict(ORDER_STATUSES)[new_status]}.", "success")
    return redirect(url_for("orders.view", order_id=order.id))


@bp.route("/<int:order_id>/payment-status", methods=["POST"])
@login_required
def update_payment_status(order_id):
    order = db.get_or_404(Order, order_id)
    new_status = request.form.get("payment_status")
    if new_status not in dict(PAYMENT_STATUSES):
        abort(400)
    order.payment_status = new_status
    db.session.commit()
    flash(f"Payment status updated to {dict(PAYMENT_STATUSES)[new_status]}.", "info")
    return redirect(url_for("orders.view", order_id=order.id))


@bp.route("/<int:order_id>/garments/new", methods=["GET", "POST"])
@login_required
def create_garment(order_id):
    order = db.get_or_404(Order, order_id)
    form = GarmentForm()
    if form.validate_on_submit():
        garment = Garment(
            order_id=order.id,
            garment_type=form.garment_type.data,
            color=form.color.data,
            brand=form.brand.data,
            description=form.description.data,
            measurements_notes=form.measurements_notes.data,
        )
        db.session.add(garment)
        db.session.flush()
        _attach_photo_if_present(form, garment)
        db.session.commit()
        flash("Garment added.", "success")
        return redirect(url_for("orders.view", order_id=order.id))
    return render_template("orders/garment_form.html", form=form, order=order, garment=None)


@bp.route("/<int:order_id>/garments/<int:garment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_garment(order_id, garment_id):
    order, garment = _get_order_garment(order_id, garment_id)
    form = GarmentForm(obj=garment)
    if form.validate_on_submit():
        garment.garment_type = form.garment_type.data
        garment.color = form.color.data
        garment.brand = form.brand.data
        garment.description = form.description.data
        garment.measurements_notes = form.measurements_notes.data
        _attach_photo_if_present(form, garment)
        db.session.commit()
        flash("Garment updated.", "success")
        return redirect(url_for("orders.view", order_id=order.id))
    return render_template("orders/garment_form.html", form=form, order=order, garment=garment)


def _attach_photo_if_present(form, garment):
    photo_file = form.photo.data
    if photo_file and getattr(photo_file, "filename", None) and allowed_file(photo_file.filename):
        filename, thumbnail_filename = save_garment_photo(
            photo_file, garment.id, current_app.config["UPLOAD_FOLDER"]
        )
        db.session.add(GarmentPhoto(garment_id=garment.id, filename=filename, thumbnail_filename=thumbnail_filename))


@bp.route("/<int:order_id>/garments/<int:garment_id>/delete", methods=["POST"])
@login_required
def delete_garment(order_id, garment_id):
    order, garment = _get_order_garment(order_id, garment_id)
    for photo in garment.photos:
        delete_garment_photo_files(photo, current_app.config["UPLOAD_FOLDER"])
    db.session.delete(garment)
    db.session.commit()
    flash("Garment removed.", "info")
    return redirect(url_for("orders.view", order_id=order.id))


@bp.route("/<int:order_id>/garments/<int:garment_id>/photos/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_photo(order_id, garment_id, photo_id):
    order, garment = _get_order_garment(order_id, garment_id)
    photo = db.get_or_404(GarmentPhoto, photo_id)
    if photo.garment_id != garment.id:
        abort(404)
    delete_garment_photo_files(photo, current_app.config["UPLOAD_FOLDER"])
    db.session.delete(photo)
    db.session.commit()
    flash("Photo removed.", "info")
    return redirect(url_for("orders.edit_garment", order_id=order.id, garment_id=garment.id))


@bp.route("/<int:order_id>/garments/<int:garment_id>/lines", methods=["POST"])
@login_required
def create_line(order_id, garment_id):
    order, garment = _get_order_garment(order_id, garment_id)
    form = OrderLineForm()
    _populate_catalog_choices(form)
    _populate_inventory_choices(form)
    if form.validate_on_submit():
        line = OrderLine(
            garment_id=garment.id,
            catalog_item_id=form.catalog_item_id.data,
            inventory_item_id=form.inventory_item_id.data,
            description=form.description.data,
            quantity=form.quantity.data,
            unit_price=form.unit_price.data,
            vat_rate=form.vat_rate.data,
            notes=form.notes.data,
        )
        db.session.add(line)
        db.session.flush()
        if line.inventory_item_id:
            touched = sync_order_line_stock(
                old_item_id=None,
                old_quantity=0,
                new_item_id=line.inventory_item_id,
                new_quantity=line.quantity,
                order_line=line,
                user=current_user,
            )
            for item in touched:
                if item.quantity_on_hand < 0:
                    flash(
                        f"Warning: “{item.name}” stock is now negative ({item.quantity_on_hand} {item.unit}).",
                        "warning",
                    )
        db.session.commit()
        flash("Alteration added.", "success")
    else:
        for field_name, errors in form.errors.items():
            label = getattr(form, field_name).label.text
            for error in errors:
                flash(f"{label}: {error}", "danger")
    return redirect(url_for("orders.view", order_id=order.id))


@bp.route("/<int:order_id>/garments/<int:garment_id>/lines/<int:line_id>/edit", methods=["GET", "POST"])
@login_required
def edit_line(order_id, garment_id, line_id):
    order, garment = _get_order_garment(order_id, garment_id)
    line = db.get_or_404(OrderLine, line_id)
    if line.garment_id != garment.id:
        abort(404)

    form = OrderLineForm(obj=line)
    catalog_items = _populate_catalog_choices(form)
    inventory_items = _populate_inventory_choices(form)
    if request.method == "GET":
        form.catalog_item_id.data = line.catalog_item_id
        form.inventory_item_id.data = line.inventory_item_id

    if form.validate_on_submit():
        old_inventory_item_id = line.inventory_item_id
        old_quantity = line.quantity

        line.catalog_item_id = form.catalog_item_id.data
        line.inventory_item_id = form.inventory_item_id.data
        line.description = form.description.data
        line.quantity = form.quantity.data
        line.unit_price = form.unit_price.data
        line.vat_rate = form.vat_rate.data
        line.notes = form.notes.data

        touched = sync_order_line_stock(
            old_item_id=old_inventory_item_id,
            old_quantity=old_quantity,
            new_item_id=line.inventory_item_id,
            new_quantity=line.quantity,
            order_line=line,
            user=current_user,
        )
        for item in touched:
            if item.quantity_on_hand < 0:
                flash(
                    f"Warning: “{item.name}” stock is now negative ({item.quantity_on_hand} {item.unit}).",
                    "warning",
                )

        db.session.commit()
        flash("Alteration updated.", "success")
        return redirect(url_for("orders.view", order_id=order.id))
    return render_template(
        "orders/line_form.html",
        form=form,
        order=order,
        garment=garment,
        line=line,
        catalog_items=catalog_items,
        inventory_items=inventory_items,
    )


@bp.route("/<int:order_id>/garments/<int:garment_id>/lines/<int:line_id>/delete", methods=["POST"])
@login_required
def delete_line(order_id, garment_id, line_id):
    order, garment = _get_order_garment(order_id, garment_id)
    line = db.get_or_404(OrderLine, line_id)
    if line.garment_id != garment.id:
        abort(404)
    if line.inventory_item_id:
        sync_order_line_stock(
            old_item_id=line.inventory_item_id,
            old_quantity=line.quantity,
            new_item_id=None,
            new_quantity=0,
            order_line=line,
            user=current_user,
        )
    db.session.delete(line)
    db.session.commit()
    flash("Alteration removed.", "info")
    return redirect(url_for("orders.view", order_id=order.id))


@bp.route("/<int:order_id>/garments/<int:garment_id>/ticket")
@login_required
def garment_ticket(order_id, garment_id):
    order, garment = _get_order_garment(order_id, garment_id)
    qr = qr_data_uri(url_for("orders.view", order_id=order.id, _external=True))
    return render_template("orders/ticket.html", order=order, garment=garment, qr_data_uri=qr)


@bp.route("/<int:order_id>/tickets")
@login_required
def order_tickets(order_id):
    order = db.get_or_404(Order, order_id)
    qr = qr_data_uri(url_for("orders.view", order_id=order.id, _external=True))
    return render_template("orders/tickets_a4.html", order=order, qr_data_uri=qr)


@bp.route("/<int:order_id>/receipt")
@login_required
def receipt(order_id):
    order = db.get_or_404(Order, order_id)
    portal_qr = None
    if order.portal_active:
        portal_qr = qr_data_uri(url_for("portal.view", token=order.portal_token, _external=True))
    settings = Settings.get_solo()
    # This document goes home with the client, so it's in their language —
    # not whichever staff member happened to print it.
    g.portal_locale = order.client.preferred_language
    return render_template("orders/receipt.html", order=order, portal_qr_data_uri=portal_qr, settings=settings)


@bp.route("/<int:order_id>/portal/revoke", methods=["POST"])
@login_required
def revoke_portal(order_id):
    order = db.get_or_404(Order, order_id)
    order.portal_revoked = True
    db.session.commit()
    flash("Client portal link revoked.", "info")
    return redirect(url_for("orders.view", order_id=order.id))


@bp.route("/<int:order_id>/portal/regenerate", methods=["POST"])
@login_required
def regenerate_portal(order_id):
    order = db.get_or_404(Order, order_id)
    order.portal_token = generate_portal_token()
    order.portal_revoked = False
    db.session.commit()
    flash("New client portal link generated — the old one no longer works.", "success")
    return redirect(url_for("orders.view", order_id=order.id))


@bp.route("/<int:order_id>/notify", methods=["POST"])
@login_required
def notify_client(order_id):
    order = db.get_or_404(Order, order_id)
    client = order.client
    if not client.consent_notifications:
        flash(f"{client.name} has opted out of notifications.", "warning")
    elif not client.email:
        flash(f"{client.name} has no email address on file.", "warning")
    else:
        log = notify_order_ready(order)
        if log.status == "sent":
            flash(f"Notified {client.name} by email.", "success")
        else:
            flash(f"Could not send the notification: {log.error_message}", "danger")
    return redirect(url_for("orders.view", order_id=order.id))
