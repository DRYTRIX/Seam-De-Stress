from flask import Blueprint, g, render_template

from app.models.order import Order
from app.models.settings import Settings

bp = Blueprint("portal", __name__, url_prefix="/portal")


@bp.route("/<token>")
def view(token):
    order = Order.query.filter_by(portal_token=token, portal_revoked=False).first()
    if order is None:
        return render_template("portal/invalid.html"), 404
    g.portal_locale = order.client.preferred_language
    settings = Settings.get_solo()
    return render_template("portal/order.html", order=order, settings=settings)
