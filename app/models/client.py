from app.extensions import db
from app.models.mixins import TimestampMixin


class Client(TimestampMixin, db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    phone = db.Column(db.String(32), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    address = db.Column(db.Text, nullable=True)
    preferred_language = db.Column(db.String(5), nullable=False, default="nl")
    notes = db.Column(db.Text, nullable=True)
    consent_notifications = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Client {self.name}>"
