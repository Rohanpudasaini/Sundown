from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import InvalidTokenError
from sqlalchemy import select
from core.auth import create_access_token, validate_access_token
from core.auth.pw_lib import verify_hash
from core.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from core.exception import AUTHENTICATION_EXCEPTION
from users.model import User, Role, Permission
from users.schema import (
    PermissionGetSchema,
    RoleGetSchema,
    TokenSchema,
    UserCreateSchema,
    UserGetSchema,
    UserPaginatedSchema,
    RolePaginatedSchema,
    PermissionPaginatedSchema,
)
import logging


app = APIRouter(prefix="/users", tags=["users"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = validate_access_token(token)
    except InvalidTokenError as e:
        logging.error(e)
        raise AUTHENTICATION_EXCEPTION
    return payload.get("sub")


@app.get(
    "/",
    response_model=UserGetSchema | UserPaginatedSchema,
    dependencies=[Depends(get_current_user)],
)
async def read_users(
    db: AsyncSession = Depends(get_db),
    id: str | None = None,
    page: int = 1,
    offset: int = 20,
):
    return await User.get(db=db, page=page, offset=offset)


@app.post("/signup", dependencies=[Depends(get_current_user)])
async def create_user(data: UserCreateSchema, db: AsyncSession = Depends(get_db)):
    return await User(**data.model_dump()).create(db=db)


@app.get(
    "/roles",
    response_model=RoleGetSchema | RolePaginatedSchema,
    dependencies=[Depends(get_current_user)],
)
async def read_roles(
    db: AsyncSession = Depends(get_db),
    id: str | None = None,
    page: int = 1,
    offset: int = 20,
):
    return await Role.get(db=db, page=page, offset=offset)


@app.get(
    "/permissions",
    response_model=PermissionGetSchema | PermissionPaginatedSchema,
    dependencies=[Depends(get_current_user)],
)
async def read_permissions(
    db: AsyncSession = Depends(get_db),
    id: str | None = None,
    page: int = 1,
    offset: int = 20,
):
    return await Permission.get(db=db, page=page, offset=offset)


@app.post("/login", response_model=TokenSchema)
async def login(
    data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    user = (
        await db.execute(select(User).where(User.email == data.username))
    ).scalar_one_or_none()
    if not user:
        raise AUTHENTICATION_EXCEPTION
    if not verify_hash(user.hashed_password, data.password):
        raise AUTHENTICATION_EXCEPTION
    return create_access_token(
        data={
            "sub": str(user.id),
            "role": str(user.role_id),
            "email": user.email,
        }
    )


@app.get("/me", response_model=UserGetSchema)
async def get_my_details(
    user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
    return user
