from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_babel import refresh as refresh_babel
from flask_login import current_user, login_required, login_user, logout_user

from app.blueprints.auth.forms import AccountForm, LoginForm
from app.extensions import db, limiter
from app.models.mixins import utcnow
from app.models.user import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit(lambda: current_app.config["LOGIN_RATE_LIMIT"], methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user is None or not user.is_active or not user.check_password(form.password.data):
            flash(_("Invalid username or password."), "danger")
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        user.last_login_at = utcnow()
        db.session.commit()

        next_page = request.args.get("next")
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = url_for("main.dashboard")
        return redirect(next_page)

    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash(_("You have been logged out."), "info")
    return redirect(url_for("auth.login"))


@bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = AccountForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.preferred_language = form.preferred_language.data
        if form.new_password.data:
            current_user.set_password(form.new_password.data)
        db.session.commit()
        # Locale is cached per-request by Flask-Babel; without this, a
        # language change wouldn't take effect until the *next* request.
        refresh_babel()
        flash(_("Account updated."), "success")
        return redirect(url_for("auth.account"))
    return render_template("auth/account.html", form=form)
