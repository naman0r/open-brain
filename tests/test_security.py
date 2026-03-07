import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import require_api_token


def test_require_api_token_accepts_valid_token() -> None:
    original = settings.open_brain_api_token
    settings.open_brain_api_token = "change-me"
    try:
        require_api_token("Bearer change-me")
    finally:
        settings.open_brain_api_token = original


def test_require_api_token_rejects_invalid_token() -> None:
    original = settings.open_brain_api_token
    settings.open_brain_api_token = "change-me"
    try:
        with pytest.raises(HTTPException) as exc:
            require_api_token("Bearer wrong")
        assert exc.value.status_code == 401
    finally:
        settings.open_brain_api_token = original

