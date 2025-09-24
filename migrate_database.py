#!/usr/bin/env python3
"""
Database migration script to add new columns for member login functionality
"""

import pymysql
import sys

# Database configuration
DB_USERNAME = 'root'
DB_PASSWORD = 'root'  # Change this to your MySQL password
DB_HOST = 'localhost'
DB_PORT = 3306
DB_NAME = 'society_app'

def migrate_database():
    """Add new columns to existing tables"""
    try:
        # Connect to MySQL database
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        print("🔄 Starting database migration...")
        
        # Add new columns to user table
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN is_member BOOLEAN DEFAULT FALSE")
            print("✅ Added 'is_member' column to user table")
        except pymysql.Error as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  'is_member' column already exists in user table")
            else:
                print(f"❌ Error adding 'is_member' column: {e}")
        
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN house_id INT")
            print("✅ Added 'house_id' column to user table")
        except pymysql.Error as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  'house_id' column already exists in user table")
            else:
                print(f"❌ Error adding 'house_id' column: {e}")
        
        try:
            cursor.execute("ALTER TABLE user ADD CONSTRAINT fk_user_house FOREIGN KEY (house_id) REFERENCES house(id)")
            print("✅ Added foreign key constraint for user.house_id")
        except pymysql.Error as e:
            if "Duplicate key name" in str(e) or "already exists" in str(e):
                print("ℹ️  Foreign key constraint already exists")
            else:
                print(f"❌ Error adding foreign key constraint: {e}")
        
        # Create complaint table
        try:
            cursor.execute("""
                CREATE TABLE complaint (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    status VARCHAR(20) DEFAULT 'Open',
                    priority VARCHAR(10) DEFAULT 'Medium',
                    created_by INT NOT NULL,
                    house_id INT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    resolved_at DATETIME NULL,
                    admin_notes TEXT NULL,
                    FOREIGN KEY (created_by) REFERENCES user(id),
                    FOREIGN KEY (house_id) REFERENCES house(id)
                )
            """)
            print("✅ Created 'complaint' table")
        except pymysql.Error as e:
            if "already exists" in str(e):
                print("ℹ️  'complaint' table already exists")
            else:
                print(f"❌ Error creating complaint table: {e}")
        
        # Commit changes
        connection.commit()
        print("✅ Database migration completed successfully!")
        
        cursor.close()
        connection.close()
        
        return True
        
    except pymysql.Error as e:
        print(f"❌ Database migration failed: {e}")
        return False

def main():
    print("🚀 Society App Database Migration")
    print("=" * 50)
    
    # Check if PyMySQL is installed
    try:
        import pymysql
    except ImportError:
        print("❌ PyMySQL is not installed. Please install it first:")
        print("   pip install PyMySQL")
        sys.exit(1)
    
    # Run migration
    if migrate_database():
        print("=" * 50)
        print("🎉 Migration completed successfully!")
        print("You can now run the Flask application with member login functionality.")
    else:
        print("=" * 50)
        print("❌ Migration failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()