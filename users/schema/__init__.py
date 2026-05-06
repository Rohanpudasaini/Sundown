from uuid import UUID

from pydantic import BaseModel, EmailStr


class PermissionGetSchema(BaseModel):
    id: UUID
    name: str
    description: str


class RoleGetSchema(BaseModel):
    id: UUID
    name: str
    description: str
    permissions: list[PermissionGetSchema]


class UserCreateSchema(BaseModel):
    email: EmailStr
    hashed_password: str


class SimpleRoleSchema(BaseModel):
    id: UUID
    name: str
    description: str


class UserGetSchema(BaseModel):
    id: UUID
    email: EmailStr
    is_superuser: bool
    role: SimpleRoleSchema | None


class UserPaginatedSchema(BaseModel):
    total: int
    page: int
    size: int
    results: list[UserGetSchema]


class RolePaginatedSchema(BaseModel):
    total: int
    page: int
    size: int
    results: list[RoleGetSchema]


class PermissionPaginatedSchema(BaseModel):
    total: int
    page: int
    size: int
    results: list[PermissionGetSchema]


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class TokenSchema(BaseModel):
    access_token: str
