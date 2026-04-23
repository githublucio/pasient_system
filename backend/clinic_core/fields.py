import os
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
import base64

class EncryptedTextField(models.TextField):
    """
    A field that encrypts text data before saving to the database
    and decrypts it when retrieved.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            # Fallback for migrations/setup if key not found
            # In production, this should always be set
            key = Fernet.generate_key()
        self.fernet = Fernet(key)

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        if isinstance(value, str):
            value = value.encode()
        encrypted = self.fernet.encrypt(value)
        return encrypted.decode()

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        try:
            decrypted = self.fernet.decrypt(value.encode())
            return decrypted.decode()
        except Exception:
            # If decryption fails (e.g., data was not encrypted), return as is
            return value

    def to_python(self, value):
        if value is None or value == '':
            return value
        if isinstance(value, str) and not value.startswith('gAAAA'): # Fernet tokens usually start with gAAAA
             # This is a bit naive but helpful during transition
             return value
        try:
            if isinstance(value, str):
                value = value.encode()
            decrypted = self.fernet.decrypt(value)
            return decrypted.decode()
        except Exception:
            return value
