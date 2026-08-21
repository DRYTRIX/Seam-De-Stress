from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

from app.constants import GARMENT_TYPES


def _optional_int(value):
    if value in (None, "", "None"):
        return None
    return int(value)


class OrderForm(FlaskForm):
    client_id = SelectField("Client", coerce=int, validators=[DataRequired()])
    promised_date = DateField("Promised date", validators=[Optional()])
    express = BooleanField("Express / priority")
    internal_notes = TextAreaField("Internal notes", validators=[Optional()])


class GarmentForm(FlaskForm):
    garment_type = SelectField("Type", choices=GARMENT_TYPES, validators=[DataRequired()])
    color = StringField("Color", validators=[Optional(), Length(max=64)])
    brand = StringField("Brand", validators=[Optional(), Length(max=64)])
    description = TextAreaField("Description", validators=[Optional()])
    measurements_notes = TextAreaField(
        "Measurements / notes", validators=[Optional()], render_kw={"placeholder": "e.g. inseam 78 cm"}
    )
    photo = FileField("Photo", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Images only.")])


class OrderLineForm(FlaskForm):
    catalog_item_id = SelectField("Alteration", coerce=_optional_int, validators=[Optional()])
    inventory_item_id = SelectField("Material", coerce=_optional_int, validators=[Optional()])
    description = StringField("Description", validators=[DataRequired(), Length(max=255)])
    quantity = IntegerField("Qty", validators=[InputRequired(), NumberRange(min=1)], default=1)
    unit_price = DecimalField(
        "Unit price (EUR)", places=2, validators=[InputRequired(), NumberRange(min=0)]
    )
    vat_rate = DecimalField(
        "VAT rate (%)", places=2, validators=[InputRequired(), NumberRange(min=0, max=100)], default=21
    )
    notes = StringField("Notes", validators=[Optional(), Length(max=255)])

    def validate_inventory_item_id(self, field):
        if field.data is not None and self.catalog_item_id.data is not None:
            raise ValidationError("Choose either an alteration or a material, not both.")
