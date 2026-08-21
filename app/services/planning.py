from collections import defaultdict
from datetime import timedelta

from app.models.order import Order


def load_level(minutes, capacity_minutes):
    if capacity_minutes <= 0:
        return "danger"
    pct = minutes / capacity_minutes
    if pct < 0.7:
        return "success"
    if pct <= 1.0:
        return "warning"
    return "danger"


def get_daily_loads(start_date, num_days, capacity_minutes):
    """List of {date, orders, minutes, capacity, load_pct, level} for each of
    ``num_days`` starting at ``start_date``. Cancelled orders don't count
    against a day's load; everything else charged to its promised_date does,
    since the point is "how much is committed for this day," not "how much
    is still outstanding" — a picked-up order was still promised (and done)
    that day."""
    end_date = start_date + timedelta(days=num_days)
    orders = (
        Order.query.filter(
            Order.promised_date >= start_date,
            Order.promised_date < end_date,
            Order.status != "cancelled",
        )
        .order_by(Order.express.desc(), Order.id)
        .all()
    )

    by_day = defaultdict(list)
    for order in orders:
        by_day[order.promised_date].append(order)

    days = []
    for offset in range(num_days):
        day = start_date + timedelta(days=offset)
        day_orders = by_day.get(day, [])
        minutes = sum(o.total_estimated_minutes for o in day_orders)
        days.append(
            {
                "date": day,
                "orders": day_orders,
                "minutes": minutes,
                "capacity": capacity_minutes,
                "load_pct": min(round(minutes / capacity_minutes * 100), 999) if capacity_minutes else 0,
                "level": load_level(minutes, capacity_minutes),
            }
        )
    return days
