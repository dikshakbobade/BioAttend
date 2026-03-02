import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('postgresql+asyncpg://biometric_user:biometric123@localhost:5432/biometric_attendance')
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT username, email FROM admin_users'))
        for row in result.fetchall():
            print(f"Current: username={row[0]}, email={row[1]}")
        await conn.execute(text("UPDATE admin_users SET email='dikshakbobade.pspl@gmail.com' WHERE username='admin'"))
        await conn.commit()
        print("Email updated to dikshakbobade.pspl@gmail.com!")
    await engine.dispose()

asyncio.run(main())
