#!/usr/bin/env python3
"""
Data validation script to compare source CSV with RDS database.
Generates comprehensive validation report in ingestion_output folder.
"""

import os
import sys
import csv
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any
import psycopg2
from psycopg2 import sql

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
CSV_FILE_PATH = os.getenv('CSV_FILE_PATH', 'orders.csv')
OUTPUT_DIR = 'ingestion_output'
SCHEMA_NAME = 'dev_orders'
TABLE_NAME = 'orders'


class ValidationReport:
    """Stores validation results and generates reports."""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.csv_row_count = 0
        self.db_row_count = 0
        self.csv_sample = []
        self.db_sample = []
        self.column_stats = {}
        self.data_quality_issues = []
        self.validation_passed = True
        self.errors = []
    
    def add_error(self, error: str):
        """Add validation error."""
        self.errors.append(error)
        self.validation_passed = False
    
    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            'validation_timestamp': self.timestamp,
            'validation_status': 'PASSED' if self.validation_passed else 'FAILED',
            'row_counts': {
                'csv_source': self.csv_row_count,
                'rds_database': self.db_row_count,
                'match': self.csv_row_count == self.db_row_count
            },
            'column_statistics': self.column_stats,
            'data_quality_issues': self.data_quality_issues,
            'errors': self.errors,
            'sample_data': {
                'csv_sample': self.csv_sample,
                'db_sample': self.db_sample
            }
        }


def get_db_connection():
    """Create database connection from environment variables."""
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT', '5432')
    database = os.getenv('DB_NAME', 'order_management')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    
    if not all([host, user, password]):
        raise ValueError("Missing required environment variables: DB_HOST, DB_USER, DB_PASSWORD")
    
    logger.info(f"Connecting to database {database} at {host}:{port}")
    
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


def parse_csv_date(date_str: str) -> str:
    """Parse date string in DD/MM/YY format to YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, '%d/%m/%y')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        return None


def read_csv_data(csv_path: str) -> Tuple[int, List[Dict], Dict]:
    """
    Read CSV file and return row count, sample data, and statistics.
    Returns: (row_count, sample_records, column_stats)
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    logger.info(f"Reading CSV file: {csv_path}")
    
    row_count = 0
    sample_records = []
    sales_values = []
    profit_values = []
    discount_values = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        
        for row in reader:
            row_count += 1
            
            # Collect sample (first 5 records)
            if len(sample_records) < 5:
                sample_records.append({
                    'row_id': row.get('Row ID'),
                    'order_id': row.get('Order ID'),
                    'order_date': parse_csv_date(row.get('Order Date')),
                    'customer_name': row.get('Customer Name'),
                    'product_name': row.get('Product Name'),
                    'sales': float(row.get('Sales', 0)),
                    'quantity': int(row.get('Quantity', 0)),
                    'profit': float(row.get('Profit', 0))
                })
            
            # Collect statistics
            try:
                sales_values.append(float(row.get('Sales', 0)))
                profit_values.append(float(row.get('Profit', 0)))
                discount_values.append(float(row.get('Discount', 0)))
            except (ValueError, TypeError):
                pass
    
    # Calculate statistics
    column_stats = {
        'sales': {
            'min': min(sales_values) if sales_values else 0,
            'max': max(sales_values) if sales_values else 0,
            'avg': sum(sales_values) / len(sales_values) if sales_values else 0,
            'sum': sum(sales_values) if sales_values else 0
        },
        'profit': {
            'min': min(profit_values) if profit_values else 0,
            'max': max(profit_values) if profit_values else 0,
            'avg': sum(profit_values) / len(profit_values) if profit_values else 0,
            'sum': sum(profit_values) if profit_values else 0
        },
        'discount': {
            'min': min(discount_values) if discount_values else 0,
            'max': max(discount_values) if discount_values else 0,
            'avg': sum(discount_values) / len(discount_values) if discount_values else 0
        }
    }
    
    logger.info(f"CSV file processed: {row_count} rows")
    return row_count, sample_records, column_stats


def read_db_data(conn) -> Tuple[int, List[Dict], Dict]:
    """
    Read database data and return row count, sample data, and statistics.
    Returns: (row_count, sample_records, column_stats)
    """
    logger.info("Reading data from RDS database")
    
    with conn.cursor() as cur:
        # Get row count
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(SCHEMA_NAME),
            sql.Identifier(TABLE_NAME)
        ))
        row_count = cur.fetchone()[0]
        
        # Get sample records
        cur.execute(sql.SQL("""
            SELECT row_id, order_id, order_date, customer_name, 
                   product_name, sales, quantity, profit
            FROM {}.{}
            ORDER BY row_id
            LIMIT 5
        """).format(
            sql.Identifier(SCHEMA_NAME),
            sql.Identifier(TABLE_NAME)
        ))
        
        sample_records = []
        for row in cur.fetchall():
            sample_records.append({
                'row_id': row[0],
                'order_id': row[1],
                'order_date': row[2].strftime('%Y-%m-%d') if row[2] else None,
                'customer_name': row[3],
                'product_name': row[4],
                'sales': float(row[5]) if row[5] else 0,
                'quantity': row[6],
                'profit': float(row[7]) if row[7] else 0
            })
        
        # Get column statistics
        cur.execute(sql.SQL("""
            SELECT 
                MIN(sales) as min_sales,
                MAX(sales) as max_sales,
                AVG(sales) as avg_sales,
                SUM(sales) as sum_sales,
                MIN(profit) as min_profit,
                MAX(profit) as max_profit,
                AVG(profit) as avg_profit,
                SUM(profit) as sum_profit,
                MIN(discount) as min_discount,
                MAX(discount) as max_discount,
                AVG(discount) as avg_discount
            FROM {}.{}
        """).format(
            sql.Identifier(SCHEMA_NAME),
            sql.Identifier(TABLE_NAME)
        ))
        
        stats = cur.fetchone()
        column_stats = {
            'sales': {
                'min': float(stats[0]) if stats[0] else 0,
                'max': float(stats[1]) if stats[1] else 0,
                'avg': float(stats[2]) if stats[2] else 0,
                'sum': float(stats[3]) if stats[3] else 0
            },
            'profit': {
                'min': float(stats[4]) if stats[4] else 0,
                'max': float(stats[5]) if stats[5] else 0,
                'avg': float(stats[6]) if stats[6] else 0,
                'sum': float(stats[7]) if stats[7] else 0
            },
            'discount': {
                'min': float(stats[8]) if stats[8] else 0,
                'max': float(stats[9]) if stats[9] else 0,
                'avg': float(stats[10]) if stats[10] else 0
            }
        }
    
    logger.info(f"Database data processed: {row_count} rows")
    return row_count, sample_records, column_stats


def compare_statistics(csv_stats: Dict, db_stats: Dict, report: ValidationReport):
    """Compare statistics between CSV and database."""
    logger.info("Comparing statistics between CSV and database")
    
    tolerance = 0.01  # 1% tolerance for floating point comparisons
    
    for column in ['sales', 'profit', 'discount']:
        for metric in ['min', 'max', 'avg', 'sum']:
            if metric not in csv_stats[column] or metric not in db_stats[column]:
                continue
            
            csv_val = csv_stats[column][metric]
            db_val = db_stats[column][metric]
            
            # Check if values match within tolerance
            if abs(csv_val - db_val) > abs(csv_val * tolerance):
                issue = f"{column}.{metric} mismatch: CSV={csv_val:.2f}, DB={db_val:.2f}"
                report.data_quality_issues.append(issue)
                logger.warning(issue)


def validate_data() -> ValidationReport:
    """Main validation function."""
    report = ValidationReport()
    
    try:
        # Create output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        logger.info(f"Output directory: {OUTPUT_DIR}")
        
        # Read CSV data
        csv_count, csv_sample, csv_stats = read_csv_data(CSV_FILE_PATH)
        report.csv_row_count = csv_count
        report.csv_sample = csv_sample
        
        # Connect to database and read data
        conn = get_db_connection()
        try:
            db_count, db_sample, db_stats = read_db_data(conn)
            report.db_row_count = db_count
            report.db_sample = db_sample
            
            # Store statistics
            report.column_stats = {
                'csv': csv_stats,
                'database': db_stats
            }
            
            # Validate row counts
            if csv_count != db_count:
                report.add_error(f"Row count mismatch: CSV has {csv_count} rows, DB has {db_count} rows")
            else:
                logger.info(f"✓ Row count validation passed: {csv_count} rows")
            
            # Compare statistics
            compare_statistics(csv_stats, db_stats, report)
            
            if not report.data_quality_issues:
                logger.info("✓ Statistical validation passed")
            
        finally:
            conn.close()
        
        # Final validation status
        if report.validation_passed and not report.data_quality_issues:
            logger.info("✓ ALL VALIDATIONS PASSED")
        else:
            logger.warning("⚠ VALIDATION ISSUES DETECTED")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        report.add_error(str(e))
    
    return report


def generate_reports(report: ValidationReport):
    """Generate validation reports in multiple formats."""
    
    # JSON report
    json_file = os.path.join(OUTPUT_DIR, f'validation_report_{report.timestamp}.json')
    with open(json_file, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)
    logger.info(f"JSON report saved: {json_file}")
    
    # Text report
    text_file = os.path.join(OUTPUT_DIR, f'validation_report_{report.timestamp}.txt')
    with open(text_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("DATA VALIDATION REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Timestamp: {report.timestamp}\n")
        f.write(f"Status: {('PASSED' if report.validation_passed else 'FAILED')}\n\n")
        
        f.write("-" * 80 + "\n")
        f.write("ROW COUNT COMPARISON\n")
        f.write("-" * 80 + "\n")
        f.write(f"CSV Source:     {report.csv_row_count:,} rows\n")
        f.write(f"RDS Database:   {report.db_row_count:,} rows\n")
        f.write(f"Match:          {'✓ YES' if report.csv_row_count == report.db_row_count else '✗ NO'}\n\n")
        
        f.write("-" * 80 + "\n")
        f.write("COLUMN STATISTICS COMPARISON\n")
        f.write("-" * 80 + "\n\n")
        
        for column in ['sales', 'profit', 'discount']:
            f.write(f"{column.upper()}:\n")
            csv_stats = report.column_stats['csv'][column]
            db_stats = report.column_stats['database'][column]
            
            f.write(f"  Min:  CSV={csv_stats['min']:>12.2f}  |  DB={db_stats['min']:>12.2f}\n")
            f.write(f"  Max:  CSV={csv_stats['max']:>12.2f}  |  DB={db_stats['max']:>12.2f}\n")
            f.write(f"  Avg:  CSV={csv_stats['avg']:>12.2f}  |  DB={db_stats['avg']:>12.2f}\n")
            if 'sum' in csv_stats:
                f.write(f"  Sum:  CSV={csv_stats['sum']:>12.2f}  |  DB={db_stats['sum']:>12.2f}\n")
            f.write("\n")
        
        f.write("-" * 80 + "\n")
        f.write("SAMPLE DATA (First 5 Records)\n")
        f.write("-" * 80 + "\n\n")
        
        f.write("CSV Sample:\n")
        for i, record in enumerate(report.csv_sample, 1):
            f.write(f"  {i}. Row ID: {record['row_id']}, Order: {record['order_id']}, "
                   f"Customer: {record['customer_name']}, Sales: ${record['sales']:.2f}\n")
        
        f.write("\nDatabase Sample:\n")
        for i, record in enumerate(report.db_sample, 1):
            f.write(f"  {i}. Row ID: {record['row_id']}, Order: {record['order_id']}, "
                   f"Customer: {record['customer_name']}, Sales: ${record['sales']:.2f}\n")
        
        if report.data_quality_issues:
            f.write("\n" + "-" * 80 + "\n")
            f.write("DATA QUALITY ISSUES\n")
            f.write("-" * 80 + "\n")
            for issue in report.data_quality_issues:
                f.write(f"  ⚠ {issue}\n")
        
        if report.errors:
            f.write("\n" + "-" * 80 + "\n")
            f.write("ERRORS\n")
            f.write("-" * 80 + "\n")
            for error in report.errors:
                f.write(f"  ✗ {error}\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    logger.info(f"Text report saved: {text_file}")
    
    # Summary file
    summary_file = os.path.join(OUTPUT_DIR, 'validation_summary.txt')
    with open(summary_file, 'w') as f:
        f.write(f"Last Validation: {report.timestamp}\n")
        f.write(f"Status: {('PASSED' if report.validation_passed else 'FAILED')}\n")
        f.write(f"CSV Rows: {report.csv_row_count:,}\n")
        f.write(f"DB Rows: {report.db_row_count:,}\n")
        f.write(f"Issues: {len(report.data_quality_issues) + len(report.errors)}\n")
    
    logger.info(f"Summary saved: {summary_file}")


def main():
    """Main entry point."""
    logger.info("Starting data validation")
    
    try:
        # Run validation
        report = validate_data()
        
        # Generate reports
        generate_reports(report)
        
        # Print summary
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Status:       {('✓ PASSED' if report.validation_passed else '✗ FAILED')}")
        print(f"CSV Rows:     {report.csv_row_count:,}")
        print(f"DB Rows:      {report.db_row_count:,}")
        print(f"Issues:       {len(report.data_quality_issues) + len(report.errors)}")
        print(f"Reports:      {OUTPUT_DIR}/")
        print("=" * 80 + "\n")
        
        return 0 if report.validation_passed else 1
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
