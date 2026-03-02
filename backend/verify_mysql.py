import pymysql
import os

DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "Password" 
DB_NAME = "biometric_attendance"

def verify_connection():
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        print("MySQL Connection: OK")
        
        # Check if audit_logs table exists
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES LIKE 'audit_logs'")
        if cursor.fetchone():
             print("Table audit_logs: OK")
        else:
             print("Table audit_logs: MISSING")
             
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"MySQL Connection: FAILED ({e})")

if __name__ == "__main__":
    verify_connection()
