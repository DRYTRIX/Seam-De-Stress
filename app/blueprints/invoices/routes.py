import csv
import io
from datetime import date

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from app.blueprints.invoices.forms import InvoiceCreateForm
from app.constants import INVOICE_STATUSES, ROLE_ADMIN
from app.extensions import db
from app.models.client import Client
from app.models.invoice import Invoice, InvoiceLine
from app.models.order import Order
from app.models.settings import Settings
from app.services.pdf import file_data_uri, render_pdf
from app.services.revenue import monthly_revenue
from app.utils.decorators import roles_required

bp = Blueprint("invoices", __name__, url_prefix="/invoices")


def _eligible_orders(client_id):
    return (
        Order.query.filter(
            Order.client_id == client_id,
            Order.invoice_id.is_(None),
            Order.status != "cancelled",
        )
        .order_by(Order.intake_date)
        .all()
    )


@bp.route("/")
@roles_required(ROLE_ADMIN)
def list_invoices():
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    query = Invoice.query.join(Client)
    if status:
        query = query.filter(Invoice.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Invoice.invoice_number.ilike(like), Client.name.ilike(like)))
    invoices = query.order_by(Invoice.issue_date.desc(), Invoice.id.desc()).all()
    return render_template(
        "invoices/list.html",
        invoices=invoices,
        status=status,
        q=q,
        statuses=INVOICE_STATUSES,
        revenue=monthly_revenue(),
    )


@bp.route("/new", methods=["GET", "POST"])
@roles_required(ROLE_ADMIN)
def create():
    client_id = request.values.get("client_id", type=int)
    clients = Client.query.order_by(Client.name).all()
    selected_client = db.session.get(Client, client_id) if client_id else None
    eligible_orders = _eligible_orders(selected_client.id) if selected_client else []

    form = InvoiceCreateForm()
    if request.method == "POST" and form.validate_on_submit():
        order_ids = {int(value) for value in request.form.getlist("order_ids")}
        orders = [o for o in eligible_orders if o.id in order_ids]
        if not selected_client or not orders:
            flash("Select at least one order to invoice.", "warning")
        else:
            invoice = Invoice(
                invoice_number=Invoice.generate_number(date.today().year),
                client_id=selected_client.id,
                due_date=form.due_date.data,
                notes=form.notes.data,
                status="draft",
            )
            db.session.add(invoice)
            db.session.flush()
            for order in orders:
                order.invoice_id = invoice.id
                for garment in order.garments:
                    for line in garment.lines:
                        db.session.add(
                            InvoiceLine(
                                invoice_id=invoice.id,
                                description=f"{order.code} — {line.description}",
                                quantity=line.quantity,
                                unit_price=line.unit_price,
                                vat_rate=line.vat_rate,
                            )
                        )
            db.session.commit()
            flash(f"Invoice {invoice.invoice_number} created.", "success")
            return redirect(url_for("invoices.view", invoice_id=invoice.id))

    return render_template(
        "invoices/form.html",
        clients=clients,
        selected_client=selected_client,
        eligible_orders=eligible_orders,
        form=form,
    )


@bp.route("/<int:invoice_id>")
@roles_required(ROLE_ADMIN)
def view(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    return render_template("invoices/view.html", invoice=invoice)


@bp.route("/<int:invoice_id>/status", methods=["POST"])
@roles_required(ROLE_ADMIN)
def update_status(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    new_status = request.form.get("status")
    if new_status not in dict(INVOICE_STATUSES):
        abort(400)
    invoice.status = new_status
    db.session.commit()
    flash(f"Invoice {invoice.invoice_number} marked as {dict(INVOICE_STATUSES)[new_status]}.", "success")
    return redirect(url_for("invoices.view", invoice_id=invoice.id))


@bp.route("/<int:invoice_id>/pdf")
@roles_required(ROLE_ADMIN)
def pdf(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    settings = Settings.get_solo()
    logo_data_uri = file_data_uri(current_app.config["UPLOAD_FOLDER"], settings.logo_filename)
    # The client receives this document, so render it in their language.
    g.portal_locale = invoice.client.preferred_language
    pdf_bytes = render_pdf("invoices/pdf.html", invoice=invoice, settings=settings, logo_data_uri=logo_data_uri)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{invoice.invoice_number}.pdf"'},
    )


@bp.route("/export.csv")
@roles_required(ROLE_ADMIN)
def export_csv():
    invoices = Invoice.query.order_by(Invoice.issue_date).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Invoice number", "Client", "Issue date", "Due date", "Status", "Subtotal", "VAT", "Total"])
    for invoice in invoices:
        writer.writerow(
            [
                invoice.invoice_number,
                invoice.client.name,
                invoice.issue_date.isoformat(),
                invoice.due_date.isoformat() if invoice.due_date else "",
                invoice.status,
                invoice.subtotal,
                invoice.vat_total,
                invoice.total,
            ]
        )
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices.csv"},
    )
