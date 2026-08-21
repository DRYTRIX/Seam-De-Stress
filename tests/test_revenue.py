from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models.invoice import Invoice, InvoiceLine
from app.services.revenue import monthly_revenue


def _make_invoice(client_id, issue_date, status, amount):
    invoice = Invoice(
        invoice_number=f"TEST-{issue_date.isoformat()}-{status}-{amount}",
        client_id=client_id,
        issue_date=issue_date,
        status=status,
    )
    db.session.add(invoice)
    db.session.flush()
    db.session.add(
        InvoiceLine(invoice_id=invoice.id, description="Line", quantity=1, unit_price=Decimal(amount), vat_rate=Decimal("0"))
    )
    db.session.commit()
    return invoice


def test_monthly_revenue_covers_requested_number_of_months(app, demo_client):
    rows = monthly_revenue(months=6)
    assert len(rows) == 6
    assert rows[-1]["year"] == date.today().year
    assert rows[-1]["month"] == date.today().month


def test_monthly_revenue_splits_invoiced_vs_paid(app, demo_client):
    today = date.today()
    _make_invoice(demo_client.id, today, "sent", "100.00")
    _make_invoice(demo_client.id, today, "paid", "50.00")

    rows = monthly_revenue(months=1)
    current = rows[0]
    assert current["invoiced"] == Decimal("150.00")
    assert current["paid"] == Decimal("50.00")


def test_monthly_revenue_ignores_invoices_outside_the_window(app, demo_client):
    old_date = date(date.today().year - 5, 1, 1)
    _make_invoice(demo_client.id, old_date, "paid", "999.00")

    rows = monthly_revenue(months=3)
    assert sum(r["invoiced"] for r in rows) == Decimal("0.00")
