from passlib.context import CryptContext
import pymysql

# Configuration
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "Password" 
DB_NAME = "biometric_attendance"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def reset_admin_password():
    new_password = "admin"
    hashed_password = pwd_context.hash(new_password)
    
    print(f"Connecting to MySQL at {DB_HOST}...")
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        print(f"Resetting password for user 'admin' to '{new_password}'...")
        cursor.execute(
            "UPDATE admin_users SET password_hash = %s WHERE username = 'admin'",
            (hashed_password,)
        )
        conn.commit()
        
        if cursor.rowcount > 0:
            print("Password updated successfully.")
        else:
            print("User 'admin' not found.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_admin_password()
