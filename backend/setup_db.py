import asyncio
import asyncpg
import os

# Default to postgres user for initial connection
# Try to connect without password first, then with 'postgres'
DB_USER = "postgres"
DB_PASS = "postgres" # Try common default
DB_HOST = "localhost"
DB_PORT = "5432"

NEW_DB = "attendance_db"
NEW_USER = "attendance_user"
NEW_PASS = "your_secure_password"

async def create_db():
    print(f"Connecting to postgres...")
    try:
        # Connect to 'postgres' database to create new db/user
        conn = await asyncpg.connect(user=DB_USER, password=DB_PASS, database='postgres', host=DB_HOST)
    except Exception as e:
        print(f"Failed to connect as {DB_USER}: {e}")
        # Try without password
        try:
             conn = await asyncpg.connect(user=DB_USER, database='postgres', host=DB_HOST)
        except Exception as e2:
             print(f"Failed to connect without password: {e2}")
             print("Please ensure PostgreSQL is running and you have a 'postgres' user.")
             return

    print("Connected. Creating user and database...")
    try:
        # Check if user exists
        user_exists = await conn.fetchval(f"SELECT 1 FROM pg_roles WHERE rolname='{NEW_USER}'")
        if not user_exists:
            await conn.execute(f"CREATE USER {NEW_USER} WITH PASSWORD '{NEW_PASS}';")
            print(f"User {NEW_USER} created.")
        else:
            print(f"User {NEW_USER} already exists.")
            
        # Check if database exists
        # asyncpg won't let us create db directly easily inside transaction? 
        # actually asyncpg setup is autocommit by default for some things? No.
        # we need to close and reopen or similar. 
        # But wait, CREATE DATABASE cannot run inside a transaction block.
        # asyncpg.connect returns a connection.
        
        # We can just try to create it.
        try:
            await conn.execute(f"CREATE DATABASE {NEW_DB} OWNER {NEW_USER};")
            print(f"Database {NEW_DB} created.")
        except asyncpg.DuplicateDatabaseError:
             print(f"Database {NEW_DB} already exists.")
        except Exception as e:
             # Check if it's because it exists (can happen if validiation fails)
             if "already exists" in str(e):
                  print(f"Database {NEW_DB} already exists.")
             else:
                  print(f"Error creating DB: {e}")

        # Grant privileges (if needed, owner should have them)
        # await conn.execute(f"GRANT ALL PRIVILEGES ON DATABASE {NEW_DB} TO {NEW_USER};")
        
    except Exception as e:
        print(f"Error during setup: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_db())
