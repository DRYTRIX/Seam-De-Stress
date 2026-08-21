from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Length, Optional

from app.constants import LANGUAGE_CHOICES


class LoginForm(FlaskForm):
    username = StringField(_l("Username"), validators=[DataRequired(), Length(max=64)])
    password = PasswordField(_l("Password"), validators=[DataRequired()])
    remember_me = BooleanField(_l("Remember me"))


class AccountForm(FlaskForm):
    full_name = StringField(_l("Full name"), validators=[DataRequired(), Length(max=128)])
    preferred_language = SelectField(_l("Language"), choices=LANGUAGE_CHOICES)
    new_password = PasswordField(_l("New password"), validators=[Optional(), Length(min=8)])
