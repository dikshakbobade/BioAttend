
import asyncio
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models.models import AdminUser

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AdminUser))
        users = result.scalars().all()
        if not users:
            print("No admin users found in database.")
        for user in users:
            print(f"User: {user.username}, Email: {user.email}, Active: {user.is_active}")

if __name__ == "__main__":
    asyncio.run(check())
