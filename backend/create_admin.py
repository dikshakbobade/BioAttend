from passlib.context import CryptContext
import pymysql
import uuid

# Configuration
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "Password" 
DB_NAME = "biometric_attendance"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin():
    username = "admin"
    password = "admin"
    email = "admin@company.com"
    hashed_password = pwd_context.hash(password)
    
    print(f"Connecting to MySQL at {DB_HOST}...")
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        print(f"Checking if user '{username}' exists...")
        cursor.execute("SELECT id FROM admin_users WHERE username = %s", (username,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"User '{username}' already exists. Updating password...")
            cursor.execute(
                "UPDATE admin_users SET password_hash = %s WHERE username = %s",
                (hashed_password, username)
            )
        else:
            print(f"User '{username}' not found. Creating...")
            # Generate UUID for ID
            user_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO admin_users (id, username, email, password_hash, role, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'SUPER_ADMIN', 1, NOW(), NOW())
                """,
                (user_id, username, email, hashed_password)
            )
            
        conn.commit()
        print("Done. Admin user should be ready.")
        print(f"Username: {username}")
        print(f"Password: {password}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_admin()
