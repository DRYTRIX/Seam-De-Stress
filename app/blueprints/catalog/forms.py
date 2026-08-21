from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional

from app.constants import CATALOG_CATEGORIES


class ServiceCatalogItemForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=128)])
    category = SelectField("Category", choices=CATALOG_CATEGORIES, validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Optional()])
    default_price = DecimalField(
        "Default price (EUR)", places=2, validators=[InputRequired(), NumberRange(min=0)]
    )
    default_vat_rate = DecimalField(
        "VAT rate (%)", places=2, validators=[InputRequired(), NumberRange(min=0, max=100)], default=21
    )
    estimated_minutes = IntegerField(
        "Estimated minutes", validators=[InputRequired(), NumberRange(min=1)], default=15
    )
    active = BooleanField("Active", default=True)
