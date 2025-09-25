#!/usr/bin/env python3
"""
Standalone script to seed the database with initial data
"""

import os
import sys
import logging

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """Main function to seed the database"""
    try:
        print("🌱 Starting database seeding...")
        
        # Import and run the seeding function
        from app.database.seed_data import seed_database
        
        success = seed_database()
        
        if success:
            print("✅ Database seeded successfully!")
            print("📊 Initial data includes:")
            print("   - Default prompts for all document types")
            print("   - Pipeline step configurations")
            print("   - System settings")
            print("   - Medical content validation prompts")
            return 0
        else:
            print("❌ Failed to seed database")
            return 1
            
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
