"""
Create admin user. Run after seed.py.
Usage: python -m scripts.create_admin
"""
import asyncio
import sys
import os
import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.db.session import AsyncSessionLocal
from core.auth.pw_lib import hash_password
from users.model import Role, User
from uuid_extension import uuid7


async def create_admin():
    print("=== Create Admin User ===")
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("ERROR: Passwords do not match.")
        sys.exit(1)

    if not username or not email or not password:
        print("ERROR: All fields required.")
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        # Check user not duplicate
        existing = (await db.execute(
            select(User).where((User.email == email) | (User.username == username))
        )).scalar_one_or_none()

        if existing:
            print(f"ERROR: User with email '{email}' or username '{username}' already exists.")
            sys.exit(1)

        # Get admin role
        admin_role = (await db.execute(
            select(Role).where(Role.name == "admin")
        )).scalar_one_or_none()

        if not admin_role:
            print("ERROR: Admin role not found. Run seed.py first.")
            sys.exit(1)

        user = User(
            id=uuid7(),
            username=username,
            email=email,
            hashed_password=hash_password(password),
            is_superuser=True,
            role_id=admin_role.id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        print(f"\nAdmin created: {user.username} ({user.email})")
        print(f"ID: {user.id}")


if __name__ == "__main__":
    asyncio.run(create_admin())
