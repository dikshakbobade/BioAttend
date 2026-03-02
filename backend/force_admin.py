
import asyncio
from app.db.database import AsyncSessionLocal, init_db
from app.services.admin_service import admin_service

async def force_create_admin():
    # Make sure tables exist
    print("Initializing tables...")
    await init_db()
    
    async with AsyncSessionLocal() as db:
        print("Creating admin user...")
        admin = await admin_service.create_initial_admin(
            db, 
            username="admin", 
            password="admin123"
        )
        if admin:
            print(f"✅ Admin user created successfully!")
            print(f"Username: {admin.username}")
            print(f"Password: admin123")
        else:
            print("⚠️ Admin user already seems to exist (or creation skipped).")

if __name__ == "__main__":
    asyncio.run(force_create_admin())
