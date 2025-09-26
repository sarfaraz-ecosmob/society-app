#!/usr/bin/env python3
"""
Database setup script for Society Maintenance App
This script creates the MySQL database and tables
"""

import pymysql
import sys
import os

# Database configuration
DB_USERNAME = 'root'
DB_PASSWORD = 'root'  # Change this to your MySQL password
DB_HOST = 'localhost'
DB_PORT = 3306
DB_NAME = 'society_app'

def create_database():
    """Create the MySQL database if it doesn't exist"""
    try:
        # Connect to MySQL server (without specifying database)
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ Database '{DB_NAME}' created successfully or already exists")
        
        cursor.close()
        connection.close()
        
        return True
        
    except pymysql.Error as e:
        print(f"❌ Error creating database: {e}")
        return False

def test_connection():
    """Test connection to the database"""
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"✅ Successfully connected to MySQL {version[0]}")
        
        cursor.close()
        connection.close()
        
        return True
        
    except pymysql.Error as e:
        print(f"❌ Error connecting to database: {e}")
        return False

def main():
    print("🚀 Setting up MySQL database for Society Maintenance App")
    print("=" * 60)
    
    # Check if PyMySQL is installed
    try:
        import pymysql
    except ImportError:
        print("❌ PyMySQL is not installed. Please install it first:")
        print("   pip install PyMySQL")
        sys.exit(1)
    
    # Create database
    if not create_database():
        print("❌ Failed to create database. Please check your MySQL configuration.")
        sys.exit(1)
    
    # Test connection
    if not test_connection():
        print("❌ Failed to connect to database. Please check your MySQL configuration.")
        sys.exit(1)
    
    print("=" * 60)
    print("✅ Database setup completed successfully!")
    print(f"📊 Database: {DB_NAME}")
    print(f"🔗 Host: {DB_HOST}:{DB_PORT}")
    print(f"👤 User: {DB_USERNAME}")
    print("=" * 60)
    print("🎉 You can now run the Flask application:")
    print("   python app.py")

if __name__ == "__main__":
    main()
