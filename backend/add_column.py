import asyncio
import asyncpg

async def add_column():
    conn = await asyncpg.connect(
        user="biometric_user",
        password="biometric123",
        database="biometric_attendance",
        host="localhost",
        port=5432
    )
    await conn.execute("ALTER TABLE attendance_logs ADD COLUMN IF NOT EXISTS working_hours FLOAT")
    await conn.close()
    print("✅ working_hours column added!")

asyncio.run(add_column())