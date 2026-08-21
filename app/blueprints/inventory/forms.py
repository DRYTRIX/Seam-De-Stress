from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional

from app.constants import INVENTORY_CATEGORIES, INVENTORY_UNIT_CHOICES, STOCK_ADJUST_REASONS


class InventoryItemForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=128)])
    sku = StringField("SKU", validators=[Optional(), Length(max=64)])
    category = SelectField("Category", choices=INVENTORY_CATEGORIES, validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Optional()])
    unit = SelectField("Unit", choices=INVENTORY_UNIT_CHOICES, validators=[DataRequired()])
    default_price = DecimalField(
        "Default price (EUR)", places=2, validators=[InputRequired(), NumberRange(min=0)]
    )
    default_vat_rate = DecimalField(
        "VAT rate (%)", places=2, validators=[InputRequired(), NumberRange(min=0, max=100)], default=21
    )
    low_stock_threshold = DecimalField(
        "Low stock threshold",
        places=2,
        validators=[Optional(), NumberRange(min=0)],
        render_kw={"placeholder": "Leave blank to use the shop default"},
    )
    active = BooleanField("Active", default=True)
    # quantity_on_hand is deliberately not a form field: it always starts at
    # 0 on create, and is only ever changed via Receive/Adjust so every
    # change is audit-logged in StockMovement.


class StockReceiveForm(FlaskForm):
    quantity = DecimalField(
        "Quantity received", places=2, validators=[InputRequired(), NumberRange(min=0.01)]
    )
    note = StringField("Note", validators=[Optional(), Length(max=255)])


class StockAdjustForm(FlaskForm):
    quantity_delta = DecimalField("Adjustment (+/-)", places=2, validators=[InputRequired()])
    reason = SelectField("Reason", choices=STOCK_ADJUST_REASONS, validators=[DataRequired()])
    note = StringField("Note", validators=[Optional(), Length(max=255)])
