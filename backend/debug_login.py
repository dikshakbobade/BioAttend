"""
Debug login - checks everything end to end
"""
import pymysql
from passlib.context import CryptContext
import asyncio
import sys
import os

# Add the backend to path
sys.path.insert(0, os.path.dirname(__file__))

DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "Password" 
DB_NAME = "biometric_attendance"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def debug():
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    cursor = conn.cursor()
    
    # 1. Check all tables
    print("=== TABLES ===")
    cursor.execute("SHOW TABLES")
    for t in cursor.fetchall():
        print(f"  {t[0]}")
    
    # 2. Check admin_users
    print("\n=== ADMIN USERS ===")
    cursor.execute("SELECT id, username, email, password_hash, is_active, role FROM admin_users")
    users = cursor.fetchall()
    if not users:
        print("  NO ADMIN USERS FOUND!")
    for u in users:
        print(f"  ID: {u[0]}")
        print(f"  Username: {u[1]}")
        print(f"  Email: {u[2]}")
        print(f"  Hash: {u[3][:30]}...")
        print(f"  Active: {u[4]}")
        print(f"  Role: {u[5]}")
        
        # 3. Verify password
        try:
            result = pwd_context.verify("admin", u[3])
            print(f"  Password 'admin' matches: {result}")
        except Exception as e:
            print(f"  Password verify error: {e}")
        
        try:
            result = pwd_context.verify("admin123", u[3])
            print(f"  Password 'admin123' matches: {result}")
        except Exception as e:
            print(f"  Password verify error: {e}")
        print()
    
    # 4. Check requests package  
    print("=== TEST LOGIN REQUESTS ===")
    import requests
    
    # Test health first
    try:
        r = requests.get("http://127.0.0.1:8000/health", timeout=5)
        print(f"  Health check: {r.status_code}")
    except Exception as e:
        print(f"  Health check failed: {e}")
    
    # Test login with 'admin'
    try:
        r = requests.post("http://127.0.0.1:8000/api/v1/admin/login", 
                         data={"username": "admin", "password": "admin", "grant_type": "password"},
                         timeout=10)
        print(f"  Login 'admin/admin': {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"  Login 'admin/admin' failed: {e}")
    
    # Test login with 'admin123'
    try:
        r = requests.post("http://127.0.0.1:8000/api/v1/admin/login", 
                         data={"username": "admin", "password": "admin123", "grant_type": "password"},
                         timeout=10)
        print(f"  Login 'admin/admin123': {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"  Login 'admin/admin123' failed: {e}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    debug()
