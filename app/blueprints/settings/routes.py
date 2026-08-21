from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from app.blueprints.settings.forms import SettingsForm
from app.constants import ROLE_ADMIN
from app.extensions import db
from app.models.settings import Settings
from app.utils.decorators import roles_required
from app.utils.uploads import allowed_file, save_logo

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/", methods=["GET", "POST"])
@roles_required(ROLE_ADMIN)
def edit():
    settings = Settings.get_solo()
    form = SettingsForm(obj=settings)
    if form.validate_on_submit():
        settings.daily_capacity_minutes = form.daily_capacity_minutes.data
        settings.default_low_stock_threshold = form.default_low_stock_threshold.data
        settings.company_name = form.company_name.data
        settings.company_address = form.company_address.data
        settings.company_phone = form.company_phone.data
        settings.opening_hours = form.opening_hours.data
        settings.portal_show_prices = form.portal_show_prices.data
        settings.company_vat_number = form.company_vat_number.data
        settings.company_iban = form.company_iban.data

        logo_file = form.logo.data
        if logo_file and getattr(logo_file, "filename", None) and allowed_file(logo_file.filename):
            settings.logo_filename = save_logo(logo_file, current_app.config["UPLOAD_FOLDER"])

        db.session.commit()
        flash("Settings updated.", "success")
        return redirect(url_for("settings.edit"))
    return render_template("settings/edit.html", form=form, settings=settings)
