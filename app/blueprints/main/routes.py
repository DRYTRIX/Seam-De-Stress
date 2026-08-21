from datetime import date, timedelta

from flask import Blueprint, current_app, render_template, request, send_from_directory
from flask_login import login_required

from app.constants import ACTIVE_ORDER_STATUSES, next_order_status
from app.extensions import db
from app.models.client import Client
from app.models.order import Garment, Order, OrderStatusLog

bp = Blueprint("main", __name__)


def _parse_order_code(q):
    cleaned = q.strip().upper().replace("SDS-", "").replace("SDS", "")
    try:
        return int(cleaned)
    except ValueError:
        return None


@bp.route("/")
@login_required
def dashboard():
    today = date.today()
    due_soon_until = today + timedelta(days=3)

    today_pickups = (
        Order.query.filter(Order.promised_date == today, Order.status.in_(ACTIVE_ORDER_STATUSES))
        .order_by(Order.id)
        .all()
    )
    due_soon = (
        Order.query.filter(
            Order.promised_date > today,
            Order.promised_date <= due_soon_until,
            Order.status.in_(ACTIVE_ORDER_STATUSES),
        )
        .order_by(Order.promised_date)
        .all()
    )
    overdue = (
        Order.query.filter(Order.promised_date < today, Order.status.in_(ACTIVE_ORDER_STATUSES))
        .order_by(Order.promised_date)
        .all()
    )
    in_progress_count = Order.query.filter_by(status="in_progress").count()
    recent_activity = (
        OrderStatusLog.query.order_by(OrderStatusLog.created_at.desc()).limit(8).all()
    )

    quick_action_orders = today_pickups + due_soon + overdue
    next_status_map = {o.id: next_order_status(o.status) for o in quick_action_orders}

    return render_template(
        "main/dashboard.html",
        today_pickups=today_pickups,
        due_soon=due_soon,
        overdue=overdue,
        in_progress_count=in_progress_count,
        recent_activity=recent_activity,
        next_status_map=next_status_map,
    )


@bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    clients, orders, garments = [], [], []

    if q:
        like = f"%{q}%"

        clients = (
            Client.query.filter(
                db.or_(Client.name.ilike(like), Client.phone.ilike(like), Client.email.ilike(like))
            )
            .order_by(Client.name)
            .limit(20)
            .all()
        )

        order_query = Order.query.join(Client)
        order_id = _parse_order_code(q)
        if order_id is not None:
            order_query = order_query.filter(Order.id == order_id)
        else:
            order_query = order_query.filter(Client.name.ilike(like))
        orders = order_query.order_by(Order.intake_date.desc()).limit(20).all()

        garments = (
            Garment.query.join(Order)
            .filter(
                db.or_(
                    Garment.description.ilike(like),
                    Garment.brand.ilike(like),
                    Garment.color.ilike(like),
                )
            )
            .order_by(Garment.id.desc())
            .limit(20)
            .all()
        )

    return render_template("main/search.html", q=q, clients=clients, orders=orders, garments=garments)


@bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@bp.route("/healthz")
def healthz():
    try:
        db.session.execute(db.text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    status = 200 if db_ok else 503
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}, status
