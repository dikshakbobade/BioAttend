import asyncio
import sys
import os

# Add current directory to path so imports work
sys.path.append(os.getcwd())

from app.db.database import init_db

async def main():
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(main())
