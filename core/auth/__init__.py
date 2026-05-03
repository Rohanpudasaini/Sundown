from datetime import datetime, timedelta, timezone

import jwt

from config import settings


def create_access_token(data: dict):
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    data["exp"] = expire
    return {
        "access_token": jwt.encode(
            payload=data, key=settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
    }


def validate_access_token(token: str):
    return jwt.decode(token, settings.SECRET_KEY, settings.ALGORITHM)
