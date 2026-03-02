import pymysql
import os

# Configuration
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "Pavilion@12345" 
DB_NAME = "biometric_attendance"

def setup_mysql():
    print(f"Connecting to MySQL at {DB_HOST}...")
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS
        )
        print("Success!")
        
        cursor = conn.cursor()
        print(f"Creating database '{DB_NAME}' if not exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print("Database created/verified.")
        
        conn.select_db(DB_NAME)
        print(f"Successfully connected to database '{DB_NAME}'.")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error connecting: {e}")
        return False

if __name__ == "__main__":
    setup_mysql()
