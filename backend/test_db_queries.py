
import asyncio
from sqlalchemy import text
from app.db.database import engine

async def test_db():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            print("Database connection test: OK")
            
            result = await conn.execute(text("SELECT COUNT(*) FROM attendance_logs"))
            count = result.scalar()
            print(f"Attendance logs count: {count}")
    except Exception as e:
        print(f"Database test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_db())
