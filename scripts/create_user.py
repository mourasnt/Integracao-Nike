import argparse
import asyncio
from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.models.user import User
from app.api.deps.hashing import get_password_hash


async def create_client_user(username: str, password_or_hash: str):
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.username == username))
        user = q.scalars().first()
        if user:
            print(f"User '{username}' already exists")
            return

        # If the provided password looks like a hash (bcrypt starts with $2), or contains a '$' (our PBKDF2 fallback format), store as-is
        if isinstance(password_or_hash, str) and (password_or_hash.startswith('$2') or ('$' in password_or_hash and len(password_or_hash) > 20)):
            password_hash = password_or_hash
        else:
            password_hash = get_password_hash(password_or_hash)

        user = User(username=username, password_hash=password_hash)
        session.add(user)
        await session.commit()
        print(f"Client user '{username}' created successfully")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('password_or_hash')
    args = parser.parse_args()
    asyncio.run(create_client_user(args.username, args.password_or_hash))