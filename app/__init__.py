import os

from flask import Flask, g, render_template, request
from flask_login import current_user

from app.config import get_config
from app.extensions import babel, csrf, db, limiter, login_manager, migrate


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)
    config_obj = config_name if isinstance(config_name, type) else get_config(config_name)
    app.config.from_object(config_obj)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    _register_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_context(app)

    from app.cli import register_cli

    register_cli(app)

    return app


def _register_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    from flask_babel import lazy_gettext as _l

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = _l("Please sign in to continue.")
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User

        return db.session.get(User, int(user_id))

    def select_locale():
        # Portal views set this to the order's client's language, since a portal
        # visitor isn't logged in and browser Accept-Language is unreliable for
        # someone reading a shared link on someone else's phone.
        portal_locale = getattr(g, "portal_locale", None)
        if portal_locale in app.config["LANGUAGES"]:
            return portal_locale
        if current_user.is_authenticated and getattr(current_user, "preferred_language", None):
            return current_user.preferred_language
        return request.accept_languages.best_match(app.config["LANGUAGES"])

    babel.init_app(app, locale_selector=select_locale)


def _register_blueprints(app):
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.catalog import bp as catalog_bp
    from app.blueprints.clients import bp as clients_bp
    from app.blueprints.inventory import bp as inventory_bp
    from app.blueprints.invoices import bp as invoices_bp
    from app.blueprints.main import bp as main_bp
    from app.blueprints.orders import bp as orders_bp
    from app.blueprints.planning import bp as planning_bp
    from app.blueprints.portal import bp as portal_bp
    from app.blueprints.settings import bp as settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(planning_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(invoices_bp)


def _register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500


def _register_context(app):
    @app.context_processor
    def inject_globals():
        from flask_babel import get_locale
        from flask_babel import gettext as _

        from app.constants import (
            INVOICE_STATUS_BADGE,
            ORDER_STATUS_BADGE,
            PAYMENT_STATUS_BADGE,
            STOCK_MOVEMENT_REASON_BADGE,
        )

        # Literal _("...") calls (not dict lookups) so `pybabel extract` can find
        # them — see CLAUDE.md's i18n section for why this shape matters.
        def category_label(code):
            return {
                "hems": _("Hems"),
                "waist": _("Waist & Fit"),
                "zippers": _("Zippers"),
                "sleeves": _("Sleeves"),
                "repairs": _("Repairs"),
                "curtains": _("Curtains & Home Textiles"),
                "other": _("Other"),
            }.get(code, code)

        def garment_type_label(code):
            return {
                "trousers": _("Trousers"),
                "dress": _("Dress"),
                "jacket": _("Jacket"),
                "curtain": _("Curtain"),
                "other": _("Other"),
            }.get(code, code)

        def order_status_label(code):
            return {
                "received": _("Received"),
                "in_progress": _("In progress"),
                "ready": _("Ready for pickup"),
                "picked_up": _("Picked up"),
                "cancelled": _("Cancelled"),
            }.get(code, code)

        def order_status_badge(code):
            return ORDER_STATUS_BADGE.get(code, "secondary")

        def payment_status_label(code):
            return {
                "unpaid": _("Unpaid"),
                "partially_paid": _("Partially paid"),
                "paid": _("Paid"),
            }.get(code, code)

        def payment_status_badge(code):
            return PAYMENT_STATUS_BADGE.get(code, "secondary")

        def invoice_status_label(code):
            return {
                "draft": _("Draft"),
                "sent": _("Sent"),
                "paid": _("Paid"),
                "overdue": _("Overdue"),
            }.get(code, code)

        def invoice_status_badge(code):
            return INVOICE_STATUS_BADGE.get(code, "secondary")

        def inventory_category_label(code):
            return {
                "thread": _("Thread & Yarn"),
                "closures": _("Buttons & Closures"),
                "zippers": _("Zippers"),
                "fabric": _("Fabric & Lining"),
                "interfacing": _("Interfacing & Stabilizers"),
                "notions": _("Notions & Trim"),
                "other": _("Other"),
            }.get(code, code)

        def inventory_unit_label(code):
            return {
                "pcs": _("Pieces"),
                "m": _("Meters"),
                "spool": _("Spool"),
                "roll": _("Roll"),
                "set": _("Set"),
                "box": _("Box"),
            }.get(code, code)

        def stock_movement_reason_label(code):
            return {
                "received": _("Stock received"),
                "consumption": _("Used on order"),
                "adjustment": _("Manual adjustment"),
                "waste": _("Waste / damaged"),
            }.get(code, code)

        def stock_movement_reason_badge(code):
            return STOCK_MOVEMENT_REASON_BADGE.get(code, "secondary")

        return {
            "app_name": app.config["APP_NAME"],
            "get_locale": get_locale,
            "category_label": category_label,
            "garment_type_label": garment_type_label,
            "order_status_label": order_status_label,
            "order_status_badge": order_status_badge,
            "payment_status_label": payment_status_label,
            "payment_status_badge": payment_status_badge,
            "invoice_status_label": invoice_status_label,
            "invoice_status_badge": invoice_status_badge,
            "inventory_category_label": inventory_category_label,
            "inventory_unit_label": inventory_unit_label,
            "stock_movement_reason_label": stock_movement_reason_label,
            "stock_movement_reason_badge": stock_movement_reason_badge,
        }
