import pytest
import uuid
from datetime import timedelta
from unittest.mock import MagicMock

from jose import jwt

from app.core.auth import create_access_token, decode_access_token
from app.config import get_settings

settings = get_settings()


def test_create_access_token_contains_subject():
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id)
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == str(user_id)


def test_create_access_token_with_expiry():
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id, expires_delta=timedelta(minutes=30))
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert "exp" in payload


def test_decode_valid_token():
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id)
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)


def test_decode_invalid_token_raises_401():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("invalid.token.here")
    assert exc_info.value.status_code == 401


def test_decode_tampered_token_raises_401():
    from fastapi import HTTPException
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id)
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(tampered)
    assert exc_info.value.status_code == 401
