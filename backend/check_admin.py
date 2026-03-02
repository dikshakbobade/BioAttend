import pymysql
import os

DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "Password" 
DB_NAME = "biometric_attendance"

def check_admin():
    print(f"Connecting to MySQL at {DB_HOST}...")
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        print("Checking admin_users table...")
        cursor.execute("SELECT username, email, is_active, role FROM admin_users")
        users = cursor.fetchall()
        
        if not users:
            print("No admin users found!")
        else:
            print("Found admin users:")
            for user in users:
                print(user)
                
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_admin()
