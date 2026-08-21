from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask_login import UserMixin

from app.constants import ROLE_ADMIN, STAFF_ROLES
from app.extensions import db
from app.models.mixins import TimestampMixin

_hasher = PasswordHasher()


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=True)
    full_name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")
    preferred_language = db.Column(db.String(5), nullable=False, default="nl")
    is_active_flag = db.Column("is_active", db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def set_password(self, raw_password):
        self.password_hash = _hasher.hash(raw_password)

    def check_password(self, raw_password):
        try:
            valid = _hasher.verify(self.password_hash, raw_password)
        except VerifyMismatchError:
            return False
        if valid and _hasher.check_needs_rehash(self.password_hash):
            self.set_password(raw_password)
        return valid

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def is_staff_role(self):
        return self.role in STAFF_ROLES

    @property
    def is_active(self):
        return self.is_active_flag

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
