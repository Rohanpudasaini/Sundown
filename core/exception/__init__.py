import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from config import settings as config


class BaseException(HTTPException):
    def __init__(
        self,
        exception_type: str,
        msg: Optional[str] = "",
        loc: Optional[List[str]] = None,
        detail: Optional[Any] = None,
        headers: Optional[Dict[str, Any]] = None,
        status_code: int = 400,
    ) -> None:
        self.msg = msg or "An error occurred."

        if detail is None:
            detail = [
                {
                    "type": exception_type,
                    "msg": self.msg,
                    **({"loc": loc} if loc else {}),
                }
            ]

        try:
            if (
                config.log_exceptions
                and str(status_code) not in config.log_exclude_exception_codes
            ):
                self.log_exception(status_code, exception_type, msg, detail)
        except Exception as e:
            # Fail silently in case of logging issues
            print(f"Logging failed: {e}")

        super().__init__(status_code=status_code, detail=detail, headers=headers)

    def log_exception(
        self, status_code: int, exception_type: str, msg: str | None, detail: Any
    ) -> None:
        logging_data = [
            str(status_code),
            getattr(config, "environment", "unknown"),  # Avoid missing attribute error
            exception_type,
            msg,
            json.dumps(detail),
        ]
        print(logging_data)


class AuthenticationError(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=401,
        )


class InternalServerError(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=500,
        )


class AuthorizationError(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=403,
        )


class BadRequest(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=400,
        )


class NotFound(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=404,
        )


AUTHENTICATION_EXCEPTION = AuthenticationError(
    exception_type="user.not_authenticated",
    msg="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

REFRESH_TOKEN_EXCEPTION = BadRequest(
    exception_type="user.invalid_refresh_token",
    msg="Could not validate refresh token",
)
