from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, DecimalField, IntegerField, StringField, TextAreaField
from wtforms.validators import InputRequired, Length, NumberRange, Optional


class SettingsForm(FlaskForm):
    daily_capacity_minutes = IntegerField(
        "Daily work-minute capacity",
        validators=[InputRequired(), NumberRange(min=1, max=1440)],
        render_kw={"placeholder": "e.g. 240 for a solo seamstress"},
    )
    default_low_stock_threshold = DecimalField(
        "Default low-stock threshold",
        places=2,
        validators=[InputRequired(), NumberRange(min=0)],
        render_kw={"placeholder": "e.g. 5"},
    )

    company_name = StringField("Shop name", validators=[Optional(), Length(max=128)])
    company_address = TextAreaField("Address", validators=[Optional()])
    company_phone = StringField("Phone", validators=[Optional(), Length(max=32)])
    opening_hours = TextAreaField(
        "Opening hours", validators=[Optional()], render_kw={"placeholder": "Mon-Fri 9:00-18:00, Sat 9:00-13:00"}
    )
    portal_show_prices = BooleanField("Show prices on the client tracking page")

    company_vat_number = StringField("VAT number", validators=[Optional(), Length(max=32)], render_kw={"placeholder": "BE 0123.456.789"})
    company_iban = StringField("IBAN", validators=[Optional(), Length(max=48)], render_kw={"placeholder": "BE00 0000 0000 0000"})
    logo = FileField("Logo", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Images only.")])
