# Data Validation Guide

## Overview

The validation script (`scripts/validate.py`) compares the source CSV file with the RDS database to ensure data integrity after ingestion.

## Quick Start

```bash
# Set environment variables
export DB_HOST=$(cd terraform && terraform output -raw rds_address)
export DB_USER=dbadmin
export DB_PASSWORD='YourSecurePassword123!'
export DB_NAME=order_management
export CSV_FILE_PATH=orders.csv

# Run validation
python3 scripts/validate.py
```

## What Gets Validated

### 1. Row Count Validation
- Compares total number of rows in CSV vs database
- **Pass Criteria:** Counts must match exactly

### 2. Statistical Validation
Compares aggregate statistics for key columns:

**Sales Column:**
- Minimum value
- Maximum value
- Average value
- Total sum

**Profit Column:**
- Minimum value
- Maximum value
- Average value
- Total sum

**Discount Column:**
- Minimum value
- Maximum value
- Average value

**Pass Criteria:** Values must match within 1% tolerance

### 3. Sample Data Comparison
- Extracts first 5 records from both sources
- Allows visual inspection of data format and content

## Output Files

All reports are saved in the `ingestion_output/` directory:

### 1. JSON Report
**File:** `validation_report_YYYYMMDD_HHMMSS.json`

Complete validation results in JSON format:
```json
{
  "validation_timestamp": "20260311_210530",
  "validation_status": "PASSED",
  "row_counts": {
    "csv_source": 9994,
    "rds_database": 9994,
    "match": true
  },
  "column_statistics": {
    "csv": {...},
    "database": {...}
  },
  "data_quality_issues": [],
  "errors": [],
  "sample_data": {...}
}
```

### 2. Text Report
**File:** `validation_report_YYYYMMDD_HHMMSS.txt`

Human-readable report with:
- Row count comparison
- Column statistics side-by-side
- Sample data from both sources
- Data quality issues (if any)
- Errors (if any)

Example:
```
================================================================================
DATA VALIDATION REPORT
================================================================================

Timestamp: 20260311_210530
Status: PASSED

--------------------------------------------------------------------------------
ROW COUNT COMPARISON
--------------------------------------------------------------------------------
CSV Source:     9,994 rows
RDS Database:   9,994 rows
Match:          ✓ YES

--------------------------------------------------------------------------------
COLUMN STATISTICS COMPARISON
--------------------------------------------------------------------------------

SALES:
  Min:  CSV=        0.44  |  DB=        0.44
  Max:  CSV=    22638.48  |  DB=    22638.48
  Avg:  CSV=      229.86  |  DB=      229.86
  Sum:  CSV=  2297200.86  |  DB=  2297200.86

PROFIT:
  Min:  CSV=    -6599.98  |  DB=    -6599.98
  Max:  CSV=     8399.98  |  DB=     8399.98
  Avg:  CSV=       28.66  |  DB=       28.66
  Sum:  CSV=   286397.02  |  DB=   286397.02
```

### 3. Summary File
**File:** `validation_summary.txt`

Quick summary of the last validation:
```
Last Validation: 20260311_210530
Status: PASSED
CSV Rows: 9,994
DB Rows: 9,994
Issues: 0
```

## Validation Status

### ✓ PASSED
All validations successful:
- Row counts match
- Statistics match within tolerance
- No data quality issues detected

### ✗ FAILED
One or more validations failed:
- Row count mismatch
- Statistical differences exceed tolerance
- Connection or file errors

## Common Issues and Solutions

### Issue: Row Count Mismatch

**Symptom:**
```
✗ Row count mismatch: CSV has 9994 rows, DB has 9000 rows
```

**Possible Causes:**
- Data load was interrupted
- Some records failed validation during load
- Data was manually modified in database

**Solution:**
1. Check load_orders_data.py logs for validation errors
2. Truncate table and reload data
3. Review invalid records in CSV

### Issue: Statistical Mismatch

**Symptom:**
```
⚠ sales.sum mismatch: CSV=2297200.86, DB=2297100.50
```

**Possible Causes:**
- Floating point precision differences
- Data type conversion issues
- Manual data modifications

**Solution:**
1. Check if difference is within acceptable range
2. Verify data types in database match CSV format
3. Review sample records for discrepancies

### Issue: Connection Timeout

**Symptom:**
```
ERROR: Database connection failed: timeout
```

**Solution:**
1. Verify RDS instance is running
2. Check security group allows your IP
3. Verify credentials are correct

## Best Practices

1. **Run validation immediately after data load**
   ```bash
   python3 scripts/load_orders_data.py && python3 scripts/validate.py
   ```

2. **Keep validation reports for audit trail**
   - Reports are timestamped
   - Store in version control or backup location

3. **Automate validation in CI/CD**
   - Add validation step to deployment pipeline
   - Fail deployment if validation fails

4. **Review sample data manually**
   - Check first 5 records in text report
   - Verify data format and content

5. **Monitor validation trends**
   - Track validation results over time
   - Alert on repeated failures

## Troubleshooting

### Debug Mode

Add verbose logging:
```bash
export LOG_LEVEL=DEBUG
python3 scripts/validate.py
```

### Manual Verification

Connect to database and run queries:
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

-- Check row count
SELECT COUNT(*) FROM dev_orders.orders;

-- Check statistics
SELECT 
  MIN(sales), MAX(sales), AVG(sales), SUM(sales),
  MIN(profit), MAX(profit), AVG(profit), SUM(profit)
FROM dev_orders.orders;

-- View sample data
SELECT * FROM dev_orders.orders ORDER BY row_id LIMIT 5;
```

### CSV Verification

Check CSV file:
```bash
# Count rows (excluding header)
wc -l orders.csv

# View first few records
head -n 6 orders.csv

# Check for data issues
grep -E "^\s*$" orders.csv  # Empty lines
```

## Integration with Terraform

Add validation to Terraform workflow:

```hcl
resource "null_resource" "validate_data" {
  provisioner "local-exec" {
    command     = "python3 ../scripts/validate.py"
    working_dir = path.module

    environment = {
      DB_HOST       = aws_db_instance.orders_db.address
      DB_PORT       = "5432"
      DB_NAME       = var.db_name
      DB_USER       = var.db_username
      DB_PASSWORD   = var.db_password
      CSV_FILE_PATH = "../orders.csv"
    }
  }

  depends_on = [null_resource.load_orders_data]
}
```

## Support

For issues or questions:
1. Check validation report for specific errors
2. Review logs from load_orders_data.py
3. Verify database connectivity
4. Check CSV file format and content
