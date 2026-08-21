from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

from app.constants import LANGUAGE_CHOICES


class ClientForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=128)])
    phone = StringField("Phone", validators=[Optional(), Length(max=32)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=255)])
    address = TextAreaField("Address", validators=[Optional()])
    preferred_language = SelectField("Preferred language", choices=LANGUAGE_CHOICES, default="nl")
    notes = TextAreaField("Notes", validators=[Optional()], render_kw={"placeholder": "e.g. always hems 2 cm shorter"})
    consent_notifications = BooleanField("OK to send status notifications (email)", default=True)
