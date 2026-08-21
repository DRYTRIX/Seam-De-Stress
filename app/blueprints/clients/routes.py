from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.blueprints.clients.forms import ClientForm
from app.extensions import db
from app.models.client import Client

bp = Blueprint("clients", __name__, url_prefix="/clients")


@bp.route("/")
@login_required
def list_clients():
    q = request.args.get("q", "").strip()
    query = Client.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Client.name.ilike(like), Client.phone.ilike(like), Client.email.ilike(like))
        )
    clients = query.order_by(Client.name).all()
    return render_template("clients/list.html", clients=clients, q=q)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ClientForm()
    if form.validate_on_submit():
        client = Client()
        form.populate_obj(client)
        db.session.add(client)
        db.session.commit()
        flash(f"Client “{client.name}” created.", "success")
        return redirect(url_for("clients.view", client_id=client.id))
    return render_template("clients/form.html", form=form, client=None)


@bp.route("/<int:client_id>")
@login_required
def view(client_id):
    client = db.get_or_404(Client, client_id)
    return render_template("clients/view.html", client=client)


@bp.route("/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def edit(client_id):
    client = db.get_or_404(Client, client_id)
    form = ClientForm(obj=client)
    if form.validate_on_submit():
        form.populate_obj(client)
        db.session.commit()
        flash(f"Client “{client.name}” updated.", "success")
        return redirect(url_for("clients.view", client_id=client.id))
    return render_template("clients/form.html", form=form, client=client)
