#!/usr/bin/env python3
"""
Data loading script for orders.csv to RDS PostgreSQL database.
Loads order data into dev_orders.orders table with validation and batch processing.
"""

import os
import sys
import csv
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection as Connection
from psycopg2.extras import execute_values

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 1000
CSV_FILE_PATH = os.getenv('CSV_FILE_PATH', 'orders.csv')
SCHEMA_NAME = 'dev_orders'
TABLE_NAME = 'orders'


class OrderRecord:
    """Represents a single order record with validation."""
    
    def __init__(self, fields: List[str]):
        """Initialize order record from CSV fields."""
        if len(fields) != 21:
            raise ValueError(f"Expected 21 fields, got {len(fields)}")
        
        self.row_id = int(fields[0]) if fields[0] else None
        self.order_id = fields[1]
        self.order_date = self._parse_date(fields[2])
        self.ship_date = self._parse_date(fields[3])
        self.ship_mode = fields[4]
        self.customer_id = fields[5]
        self.customer_name = fields[6]
        self.segment = fields[7]
        self.country = fields[8]
        self.city = fields[9]
        self.state = fields[10]
        self.postal_code = fields[11]
        self.region = fields[12]
        self.product_id = fields[13]
        self.category = fields[14]
        self.sub_category = fields[15]
        self.product_name = fields[16]
        self.sales = float(fields[17]) if fields[17] else None
        self.quantity = int(fields[18]) if fields[18] else None
        self.discount = float(fields[19]) if fields[19] else None
        self.profit = float(fields[20]) if fields[20] else None
    
    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """Parse date string in DD/MM/YY format."""
        if not date_str:
            return None
        try:
            # Parse DD/MM/YY format
            return datetime.strptime(date_str, '%d/%m/%y').date()
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}")
            return None
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate order record according to business rules.
        Returns (is_valid, error_message).
        """
        # Check row_id is positive
        if self.row_id is None or self.row_id <= 0:
            return False, f"Invalid row_id: {self.row_id}"
        
        # Check order_id is not empty
        if not self.order_id or self.order_id.strip() == '':
            return False, f"Empty order_id for row {self.row_id}"
        
        # Check discount range (0 to 1)
        if self.discount is not None and (self.discount < 0 or self.discount > 1):
            return False, f"Discount out of range [0,1]: {self.discount} for row {self.row_id}"
        
        # Check date logic: ship_date >= order_date
        if self.order_date and self.ship_date:
            if self.ship_date < self.order_date:
                return False, f"Ship date before order date for row {self.row_id}"
        
        return True, None
    
    def to_tuple(self) -> tuple:
        """Convert record to tuple for database insertion."""
        return (
            self.row_id,
            self.order_id,
            self.order_date,
            self.ship_date,
            self.ship_mode,
            self.customer_id,
            self.customer_name,
            self.segment,
            self.country,
            self.city,
            self.state,
            self.postal_code,
            self.region,
            self.product_id,
            self.category,
            self.sub_category,
            self.product_name,
            self.sales,
            self.quantity,
            self.discount,
            self.profit
        )


def get_db_connection() -> Connection:
    """
    Create database connection from environment variables.
    Expected environment variables:
    - DB_HOST: RDS endpoint hostname
    - DB_PORT: PostgreSQL port (default 5432)
    - DB_NAME: Database name (default order_management)
    - DB_USER: Database username
    - DB_PASSWORD: Database password
    """
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT', '5432')
    database = os.getenv('DB_NAME', 'order_management')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    
    if not all([host, user, password]):
        raise ValueError("Missing required environment variables: DB_HOST, DB_USER, DB_PASSWORD")
    
    logger.info(f"Connecting to database {database} at {host}:{port}")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            sslmode='require',
            connect_timeout=10
        )
        logger.info("Database connection established")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise


def check_existing_data(conn: Connection) -> int:
    """Check if orders table already contains data. Returns row count."""
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(SCHEMA_NAME),
            sql.Identifier(TABLE_NAME)
        ))
        count = cur.fetchone()[0]
        logger.info(f"Existing row count in {SCHEMA_NAME}.{TABLE_NAME}: {count}")
        return count


def read_and_validate_csv(csv_path: str) -> List[OrderRecord]:
    """
    Read CSV file and validate records.
    Returns list of valid OrderRecord objects.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    valid_records = []
    invalid_count = 0
    
    logger.info(f"Reading CSV file: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        # CSV is tab-separated
        reader = csv.reader(f, delimiter='\t')
        
        # Skip header row
        header = next(reader)
        logger.info(f"CSV header: {len(header)} columns")
        
        for line_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
            try:
                record = OrderRecord(row)
                is_valid, error_msg = record.validate()
                
                if is_valid:
                    valid_records.append(record)
                else:
                    invalid_count += 1
                    logger.warning(f"Line {line_num}: {error_msg}")
            
            except (ValueError, IndexError) as e:
                invalid_count += 1
                logger.warning(f"Line {line_num}: Failed to parse - {e}")
    
    logger.info(f"CSV processing complete: {len(valid_records)} valid, {invalid_count} invalid")
    return valid_records


def insert_batch(conn: Connection, records: List[OrderRecord]) -> int:
    """
    Insert a batch of records into the database using execute_values for better performance.
    Returns number of rows inserted.
    """
    if not records:
        return 0
    
    insert_query = sql.SQL("""
        INSERT INTO {}.{} (
            row_id, order_id, order_date, ship_date, ship_mode,
            customer_id, customer_name, segment, country, city,
            state, postal_code, region, product_id, category,
            sub_category, product_name, sales, quantity, discount, profit
        ) VALUES %s
    """).format(
        sql.Identifier(SCHEMA_NAME),
        sql.Identifier(TABLE_NAME)
    )
    
    with conn.cursor() as cur:
        try:
            # Execute batch insert using execute_values (much faster than executemany)
            data = [record.to_tuple() for record in records]
            execute_values(cur, insert_query.as_string(conn), data, page_size=1000)
            conn.commit()
            return len(records)
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Batch insert failed: {e}")
            raise


def load_data(conn: Connection, csv_path: str) -> int:
    """
    Main data loading function.
    Returns total number of rows loaded.
    """
    # Check if data already exists
    existing_count = check_existing_data(conn)
    if existing_count > 0:
        logger.info(f"Table already contains {existing_count} rows. Skipping data load.")
        return existing_count
    
    # Read and validate CSV
    valid_records = read_and_validate_csv(csv_path)
    
    if not valid_records:
        logger.warning("No valid records to load")
        return 0
    
    # Insert in batches
    total_inserted = 0
    batch = []
    
    for i, record in enumerate(valid_records, start=1):
        batch.append(record)
        
        # Insert when batch is full or at end of records
        if len(batch) >= BATCH_SIZE or i == len(valid_records):
            inserted = insert_batch(conn, batch)
            total_inserted += inserted
            logger.info(f"Inserted batch: {inserted} rows (total: {total_inserted}/{len(valid_records)})")
            batch = []
    
    # Verify final count
    final_count = check_existing_data(conn)
    if final_count != total_inserted:
        logger.error(f"Row count mismatch! Expected {total_inserted}, found {final_count}")
        raise ValueError("Data verification failed")
    
    logger.info(f"Data load complete: {total_inserted} rows inserted successfully")
    return total_inserted


def main():
    """Main entry point."""
    try:
        # Get database connection
        conn = get_db_connection()
        
        try:
            # Load data
            rows_loaded = load_data(conn, CSV_FILE_PATH)
            logger.info(f"SUCCESS: Loaded {rows_loaded} rows")
            return 0
        
        finally:
            conn.close()
            logger.info("Database connection closed")
    
    except Exception as e:
        logger.error(f"FAILED: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
