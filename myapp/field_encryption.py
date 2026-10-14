"""Deterministic encryption for patient identity columns.

The same name always produces the same ciphertext, so the app can still match
an exact birthdate. A person reading the table sees the ciphertext. The app
decrypts it when it loads the row.
"""
from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from django.conf import settings

PREFIX = 'enc1:'


def _key() -> bytes:
    secret = os.environ.get('FIELD_ENCRYPTION_KEY') or settings.SECRET_KEY
    return hashlib.sha256(secret.encode('utf-8')).digest()


def is_encrypted(value) -> bool:
    return isinstance(value, str) and value.startswith(PREFIX)


def encrypt_text(value):
    if value is None:
        return None
    text = str(value)
    if text == '' or is_encrypted(text):
        return text
    token = AESSIV(_key()).encrypt(text.encode('utf-8'), [b'pulse-identity'])
    return PREFIX + base64.urlsafe_b64encode(token).decode('ascii')


def decrypt_text(value):
    if value is None:
        return None
    text = str(value)
    if text == '' or not is_encrypted(text):
        return text
    raw = base64.urlsafe_b64decode(text[len(PREFIX):].encode('ascii'))
    return AESSIV(_key()).decrypt(raw, [b'pulse-identity']).decode('utf-8')


def scrub_identity_from_remarks(remarks: str | None) -> str:
    """Remove name and address lines that were copied into remarks."""
    if not remarks:
        return remarks or ''
    kept = []
    for part in str(remarks).split('|'):
        text = part.strip()
        if not text:
            continue
        lowered = text.casefold()
        if lowered.startswith('patient:') or lowered.startswith('address:'):
            continue
        kept.append(text)
    return ' | '.join(kept)
