#!/bin/bash
# Quick validation script

set -e

echo "=========================================="
echo "RDS Order Management Data Validation"
echo "=========================================="
echo ""

# Check if terraform directory exists
if [ ! -d "terraform" ]; then
    echo "Error: terraform directory not found"
    echo "Please run this script from the project root"
    exit 1
fi

# Check if orders.csv exists
if [ ! -f "orders.csv" ]; then
    echo "Error: orders.csv not found"
    exit 1
fi

# Get RDS endpoint from Terraform
echo "Getting RDS endpoint from Terraform..."
cd terraform
DB_HOST=$(terraform output -raw rds_address 2>/dev/null)
if [ -z "$DB_HOST" ]; then
    echo "Error: Could not get RDS endpoint from Terraform"
    echo "Make sure Terraform has been applied successfully"
    exit 1
fi
cd ..

echo "RDS Host: $DB_HOST"
echo ""

# Prompt for password if not set
if [ -z "$DB_PASSWORD" ]; then
    echo -n "Enter database password: "
    read -s DB_PASSWORD
    echo ""
fi

# Set environment variables
export DB_HOST
export DB_PORT=5432
export DB_NAME=order_management
export DB_USER=dbadmin
export DB_PASSWORD
export CSV_FILE_PATH=orders.csv

# Run validation
echo "Running validation..."
echo ""
python3 scripts/validate.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Validation completed successfully"
    echo "Reports available in: ingestion_output/"
else
    echo ""
    echo "✗ Validation failed"
    echo "Check reports in: ingestion_output/"
    exit 1
fi
