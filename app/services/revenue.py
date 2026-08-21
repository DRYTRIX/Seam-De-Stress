from datetime import date
from decimal import Decimal

from app.models.invoice import Invoice


def monthly_revenue(months=6):
    """Last ``months`` months (oldest first, including the current one):
    [{"year", "month", "invoiced", "paid"}]. Plain Python aggregation over
    all invoices — fine at this shop's scale, same tradeoff as the planning
    service."""
    today = date.today()
    periods = []
    year, month = today.year, today.month
    for _ in range(months):
        periods.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    periods.reverse()

    invoices = Invoice.query.all()
    results = []
    for year, month in periods:
        in_period = [inv for inv in invoices if inv.issue_date.year == year and inv.issue_date.month == month]
        invoiced = sum((inv.total for inv in in_period), Decimal("0.00"))
        paid = sum((inv.total for inv in in_period if inv.status == "paid"), Decimal("0.00"))
        results.append({"year": year, "month": month, "invoiced": invoiced, "paid": paid})
    return results
