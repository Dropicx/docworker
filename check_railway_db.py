#!/usr/bin/env python3
"""
Check Railway PostgreSQL database for universal_prompts table
"""

import os
import sys
from sqlalchemy import create_engine, text

# Set the Railway database URL
DATABASE_URL = "postgresql://postgres:XQrqrRwVpDGQItiGmfssbwCRbAbdKfKu@turntable.proxy.rlwy.net:37545/railway"

def check_database():
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            print("🔍 Checking Railway PostgreSQL database...")
            
            # Check if universal_prompts table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'universal_prompts'
                );
            """))
            table_exists = result.scalar()
            print(f"universal_prompts table exists: {table_exists}")
            
            if table_exists:
                # Check if it has data
                result = conn.execute(text("SELECT COUNT(*) FROM universal_prompts"))
                count = result.scalar()
                print(f"universal_prompts table has {count} records")
                
                # Show the structure
                result = conn.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'universal_prompts'
                    ORDER BY ordinal_position;
                """))
                columns = result.fetchall()
                print("\nTable structure:")
                for col in columns:
                    print(f"  {col[0]}: {col[1]}")
            else:
                print("❌ universal_prompts table does not exist")
                
            # Check what tables do exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = result.fetchall()
            print("\n📋 Existing tables:")
            for table in tables:
                print(f"  - {table[0]}")
                
            # Check document_prompts table structure
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'document_prompts'
                ORDER BY ordinal_position;
            """))
            columns = result.fetchall()
            print("\n📝 document_prompts table structure:")
            for col in columns:
                print(f"  {col[0]}: {col[1]}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_database()
