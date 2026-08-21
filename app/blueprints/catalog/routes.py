from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.blueprints.catalog.forms import ServiceCatalogItemForm
from app.constants import CATALOG_CATEGORIES, ROLE_ADMIN
from app.extensions import db
from app.models.catalog import ServiceCatalogItem
from app.utils.decorators import roles_required

bp = Blueprint("catalog", __name__, url_prefix="/catalog")


@bp.route("/")
@login_required
def list_items():
    category = request.args.get("category", "")
    query = ServiceCatalogItem.query
    if category:
        query = query.filter_by(category=category)
    items = query.order_by(ServiceCatalogItem.category, ServiceCatalogItem.name).all()
    return render_template(
        "catalog/list.html", items=items, categories=CATALOG_CATEGORIES, selected_category=category
    )


@bp.route("/new", methods=["GET", "POST"])
@roles_required(ROLE_ADMIN)
def create():
    form = ServiceCatalogItemForm()
    if form.validate_on_submit():
        item = ServiceCatalogItem()
        form.populate_obj(item)
        db.session.add(item)
        db.session.commit()
        flash(f"Catalog item “{item.name}” created.", "success")
        return redirect(url_for("catalog.list_items"))
    return render_template("catalog/form.html", form=form, item=None)


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@roles_required(ROLE_ADMIN)
def edit(item_id):
    item = db.get_or_404(ServiceCatalogItem, item_id)
    form = ServiceCatalogItemForm(obj=item)
    if form.validate_on_submit():
        form.populate_obj(item)
        db.session.commit()
        flash(f"Catalog item “{item.name}” updated.", "success")
        return redirect(url_for("catalog.list_items"))
    return render_template("catalog/form.html", form=form, item=item)


@bp.route("/<int:item_id>/toggle-active", methods=["POST"])
@roles_required(ROLE_ADMIN)
def toggle_active(item_id):
    item = db.get_or_404(ServiceCatalogItem, item_id)
    item.active = not item.active
    db.session.commit()
    flash(f"“{item.name}” is now {'active' if item.active else 'inactive'}.", "info")
    return redirect(url_for("catalog.list_items", category=request.form.get("category", "")))
