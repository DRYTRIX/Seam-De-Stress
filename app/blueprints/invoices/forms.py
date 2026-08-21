from flask_wtf import FlaskForm
from wtforms import DateField, TextAreaField
from wtforms.validators import Optional


class InvoiceCreateForm(FlaskForm):
    due_date = DateField("Due date", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
