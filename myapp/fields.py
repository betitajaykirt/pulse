"""Model fields that encrypt identity values on the way into the database."""
from __future__ import annotations

from datetime import date, datetime

from django.db import models

from myapp.field_encryption import decrypt_text, encrypt_text


class EncryptedTextField(models.TextField):
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return decrypt_text(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ''):
            return value
        return encrypt_text(value)


class EncryptedDateField(models.DateField):
    def from_db_value(self, value, expression, connection):
        if value in (None, ''):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        plain = decrypt_text(str(value))
        if not plain:
            return None
        return datetime.strptime(plain[:10], '%Y-%m-%d').date()

    def get_prep_value(self, value):
        if value in (None, ''):
            return None
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            plain = value.isoformat()
        else:
            plain = str(value)[:10]
        return encrypt_text(plain)

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
        return value
