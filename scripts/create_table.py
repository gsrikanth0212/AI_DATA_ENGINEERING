#!/usr/bin/env python3
"""
Create orders table in RDS PostgreSQL database.
"""

import os
import sys
import psycopg2

def create_table():
    """Create the orders table if it doesn't exist."""
    
    # Get connection parameters from environment
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT', '5432')
    database = os.getenv('DB_NAME', 'order_management')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    
    if not all([host, user, password]):
        print("ERROR: Missing required environment variables: DB_HOST, DB_USER, DB_PASSWORD")
        return 1
    
    print(f"Connecting to {database} at {host}:{port}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            sslmode='require',
            connect_timeout=10
        )
        
        print("Connected successfully")
        
        # Create table
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dev_orders.orders (
                    row_id INTEGER PRIMARY KEY,
                    order_id VARCHAR(50) NOT NULL,
                    order_date DATE,
                    ship_date DATE,
                    ship_mode VARCHAR(50),
                    customer_id VARCHAR(50),
                    customer_name VARCHAR(100),
                    segment VARCHAR(50),
                    country VARCHAR(100),
                    city VARCHAR(100),
                    state VARCHAR(100),
                    postal_code VARCHAR(20),
                    region VARCHAR(50),
                    product_id VARCHAR(50),
                    category VARCHAR(50),
                    sub_category VARCHAR(50),
                    product_name VARCHAR(255),
                    sales DECIMAL(10,2),
                    quantity INTEGER,
                    discount DECIMAL(5,2),
                    profit DECIMAL(10,4)
                )
            """)
            conn.commit()
            print("Table dev_orders.orders created successfully")
        
        conn.close()
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(create_table())
