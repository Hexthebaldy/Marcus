import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet

from .config import settings


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def digest(value: str):
    return hmac.new(settings.secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def normalize_email(value: str):
    local, domain = value.strip().rsplit("@", 1)
    return local + "@" + domain.lower()


def cipher():
    key = (
        settings.encryption_key
        or base64.urlsafe_b64encode(
            hashlib.sha256((settings.secret_key + ":encryption").encode()).digest()
        ).decode()
    )
    return Fernet(key.encode())


def encrypt(value: str):
    return cipher().encrypt(value.encode()).decode()


def decrypt(value: str):
    return cipher().decrypt(value.encode()).decode()


def access_token(user_id: str, session_id: str):
    return jwt.encode(
        {
            "sub": user_id,
            "sid": session_id,
            "iss": "marcus",
            "aud": "marcus-api",
            "iat": now(),
            "exp": now() + timedelta(minutes=15),
        },
        settings.secret_key,
        algorithm="HS256",
    )


def decode_token(token: str):
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=["HS256"],
        issuer="marcus",
        audience="marcus-api",
        options={"require": ["exp", "sub", "sid"]},
    )


def new_refresh():
    return secrets.token_urlsafe(48)
