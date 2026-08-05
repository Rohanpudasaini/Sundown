"""
Seed roles and permissions. Run once after migrations.
Usage: python -m scripts.seed
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.db.session import AsyncSessionLocal
from users.model import Permission, Role

PERMISSIONS = [
    # Entries
    ("entries:read", "Read own journal entries"),
    ("entries:write", "Create and edit own journal entries"),
    ("entries:delete", "Delete own journal entries"),
    ("entries:export", "Export own entries to PDF/CSV"),
    # Summaries
    ("summaries:weekly:read", "View own weekly summaries"),
    ("summaries:monthly:read", "View own monthly summaries"),
    ("summaries:generate", "Trigger AI summary generation"),
    # Admin — user management
    ("admin:users:read", "List and view all users"),
    ("admin:users:write", "Create and edit users"),
    ("admin:users:delete", "Delete or deactivate users"),
    # Admin — roles
    ("admin:roles:read", "View roles and permissions"),
    ("admin:roles:write", "Create and assign roles"),
    # Admin — entries (moderation)
    ("admin:entries:read", "Read any user's entries"),
    ("admin:entries:delete", "Delete any user's entries"),
    # Admin — system
    ("admin:system:config", "Modify system-level configuration"),
]

ROLES = {
    "user": {
        "description": "Default role for registered users",
        "permissions": [
            "entries:read",
            "entries:write",
            "entries:delete",
            "entries:export",
            "summaries:weekly:read",
            "summaries:monthly:read",
            "summaries:generate",
        ],
    },
    "moderator": {
        "description": "Can view and moderate all entries",
        "permissions": [
            "entries:read",
            "entries:write",
            "entries:delete",
            "entries:export",
            "summaries:weekly:read",
            "summaries:monthly:read",
            "summaries:generate",
            "admin:entries:read",
            "admin:entries:delete",
            "admin:users:read",
        ],
    },
    "admin": {
        "description": "Full system access",
        "permissions": [p[0] for p in PERMISSIONS],
    },
}


async def seed():
    async with AsyncSessionLocal() as db:
        # Upsert permissions
        perm_map: dict[str, Permission] = {}
        for name, description in PERMISSIONS:
            existing = (
                await db.execute(select(Permission).where(Permission.name == name))
            ).scalar_one_or_none()

            if existing:
                perm_map[name] = existing
                print(f"  [skip] permission '{name}' exists")
            else:
                perm = Permission(name=name, description=description)
                db.add(perm)
                await db.flush()
                perm_map[name] = perm
                print(f"  [+] permission '{name}'")

        # Upsert roles + assign permissions
        for role_name, role_def in ROLES.items():
            existing = (
                await db.execute(
                    select(Role)
                    .where(Role.name == role_name)
                    .options(selectinload(Role.permissions))
                )
            ).scalar_one_or_none()

            if existing:
                role = existing
                print(f"  [skip] role '{role_name}' exists")
            else:
                role = Role(name=role_name, description=role_def["description"])
                role.permissions = []
                db.add(role)
                await db.flush()
                print(f"  [+] role '{role_name}'")

            # Sync permissions (add missing, leave existing)
            current_perm_names = {p.name for p in role.permissions}
            for perm_name in role_def["permissions"]:
                if perm_name not in current_perm_names:
                    role.permissions.append(perm_map[perm_name])

        await db.commit()
        print("\nSeed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
