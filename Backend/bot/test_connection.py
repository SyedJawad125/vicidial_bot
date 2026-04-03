import os
import sys
from decouple import config
import psycopg2

# Add your project path
sys.path.append('F:/vicidial_bot/vicidial_bot')

try:
    print("Testing database connection...")
    print(f"Database: {config('POSTGRES_DB')}")
    print(f"User: {config('POSTGRES_USER')}")
    print(f"Host: {config('POSTGRES_HOST')}")
    print(f"Port: {config('POSTGRES_PORT')}")
    
    conn = psycopg2.connect(
        database=config('POSTGRES_DB'),
        user=config('POSTGRES_USER'),
        password=config('POSTGRES_PASSWORD'),
        host=config('POSTGRES_HOST'),
        port=config('POSTGRES_PORT')
    )
    print("✅ Database connection successful!")
    conn.close()
    
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check if PostgreSQL is running")
    print("2. Verify POSTGRES_PASSWORD in .env file")
    print("3. Check if database 'vicidial_bot_db' exists")
    print("4. If database doesn't exist, create it: CREATE DATABASE vicidial_bot_db;")