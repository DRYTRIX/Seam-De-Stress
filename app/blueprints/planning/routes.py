from datetime import date, timedelta

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.constants import ACTIVE_ORDER_STATUSES
from app.models.order import Order
from app.models.settings import Settings
from app.services.planning import get_daily_loads

bp = Blueprint("planning", __name__, url_prefix="/planning")


def _monday_of(day):
    return day - timedelta(days=day.weekday())


@bp.route("/")
@login_required
def view():
    try:
        anchor = date.fromisoformat(request.args.get("week", ""))
    except ValueError:
        anchor = date.today()
    monday = _monday_of(anchor)

    settings = Settings.get_solo()
    days = get_daily_loads(monday, 7, settings.daily_capacity_minutes)

    today = date.today()
    overdue = (
        Order.query.filter(Order.promised_date < today, Order.status.in_(ACTIVE_ORDER_STATUSES))
        .order_by(Order.promised_date)
        .all()
    )
    express_orders = (
        Order.query.filter(Order.express.is_(True), Order.status.in_(ACTIVE_ORDER_STATUSES))
        .order_by(Order.promised_date.is_(None), Order.promised_date)
        .all()
    )

    return render_template(
        "planning/view.html",
        days=days,
        week_start=monday,
        prev_week=(monday - timedelta(days=7)).isoformat(),
        next_week=(monday + timedelta(days=7)).isoformat(),
        this_week=_monday_of(today).isoformat(),
        overdue=overdue,
        express_orders=express_orders,
        capacity_minutes=settings.daily_capacity_minutes,
        today=today,
    )
