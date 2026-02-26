"""CLI utilities for namgun-workspace.

Usage:
    python -m app.cli seed-admin --username admin --password secret
    python -m app.cli seed-admin  # uses ADMIN_USERNAME / ADMIN_PASSWORD env vars
"""

import argparse
import asyncio
import os
import sys

from sqlalchemy import select

from app.auth.password import hash_password
from app.db.models import Base, User
from app.db.session import async_session, engine


async def seed_admin(
    username: str,
    password: str,
    display_name: str | None = None,
) -> None:
    """Create or promote an admin user.

    - If the user already exists → set is_admin=True (no password change).
    - If the user does not exist → create with is_admin=True, is_active=True,
      email_verified=True.
    """
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    domain = os.environ.get("DOMAIN", "localhost")
    email = f"{username}@{domain}"

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if user:
            if user.is_admin:
                print(f"[SEED] Admin '{username}' already exists — skipped")
            else:
                user.is_admin = True
                await session.commit()
                print(f"[SEED] User '{username}' promoted to admin")
        else:
            user = User(
                username=username,
                password_hash=hash_password(password),
                display_name=display_name or username,
                email=email,
                is_admin=True,
                is_active=True,
                email_verified=True,
            )
            session.add(user)
            await session.commit()
            print(f"[SEED] Admin '{username}' created ({email})")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli", description="Workspace CLI")
    sub = parser.add_subparsers(dest="command")

    seed = sub.add_parser("seed-admin", help="Create or promote an admin user")
    seed.add_argument(
        "--username",
        default=os.environ.get("ADMIN_USERNAME", ""),
        help="Admin username (default: $ADMIN_USERNAME)",
    )
    seed.add_argument(
        "--password",
        default=os.environ.get("ADMIN_PASSWORD", ""),
        help="Admin password (default: $ADMIN_PASSWORD)",
    )
    seed.add_argument(
        "--display-name",
        default=None,
        help="Display name (default: same as username)",
    )

    args = parser.parse_args()

    if args.command == "seed-admin":
        if not args.username or not args.password:
            print("ERROR: --username and --password are required "
                  "(or set ADMIN_USERNAME / ADMIN_PASSWORD env vars)")
            sys.exit(1)
        asyncio.run(seed_admin(args.username, args.password, args.display_name))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
