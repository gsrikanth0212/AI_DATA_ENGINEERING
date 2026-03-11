# RDS Ingestion Project AI

Terraform infrastructure for AWS RDS PostgreSQL with automated data loading and validation.

## Overview

This project provisions:
- VPC with 2 subnets across multiple availability zones
- Security group for PostgreSQL access
- RDS PostgreSQL instance (db.t3.micro)
- Database schema (`dev_orders`)
- Orders table with 21 columns
- Automated data loading from `orders.csv`

## Prerequisites

1. **AWS CLI** configured with credentials
   ```bash
   aws configure
   ```

2. **Terraform** >= 1.5.0
   ```bash
   terraform --version
   ```

3. **PostgreSQL client** (psql)
   ```bash
   # macOS
   brew install postgresql
   
   # Ubuntu/Debian
   sudo apt-get install postgresql-client
   ```

4. **Python 3** with pip
   ```bash
   python3 --version
   pip3 install -r scripts/requirements.txt
   ```

5. **orders.csv file** in the project root directory

## Quick Start

### 1. Configure Variables

Create `terraform/terraform.tfvars`:

```hcl
aws_region = "us-east-1"

# Database Configuration
db_password = "YourSecurePassword123!"  # Change this!
db_username = "dbadmin"
db_name     = "order_management"

# Optional: Override defaults
# db_instance_class    = "db.t3.micro"
# db_allocated_storage = 20
```

**Security Note:** Never commit `terraform.tfvars` to version control!

### 2. Initialize Terraform

```bash
cd terraform
terraform init
```

### 3. Review Plan

```bash
terraform plan
```

### 4. Deploy Infrastructure

```bash
terraform apply
```

This will:
- Create VPC and networking (2-3 minutes)
- Provision RDS instance (5-8 minutes)
- Create schema and table (30 seconds)
- Load data from CSV (10-30 seconds)

**Total time:** ~10-15 minutes

### 5. Verify Deployment

```bash
# Get RDS endpoint
terraform output rds_endpoint

# Connect to database
PGPASSWORD='YourPassword' psql -h $(terraform output -raw rds_address) \
  -U dbadmin -d order_management

# Check data
SELECT COUNT(*) FROM dev_orders.orders;
```

## Project Structure

```
rds_ingestion_project_ai/
├── terraform/
│   ├── main.tf                 # Main infrastructure configuration
│   ├── variables.tf            # Input variables
│   ├── outputs.tf              # Output values
│   ├── terraform.tfvars.example # Example variables file
│   └── .gitignore              # Terraform gitignore
├── scripts/
│   ├── load_orders_data.py     # Data loading script
│   ├── create_table.py         # Table creation script
│   ├── validate.py             # Data validation script
│   └── requirements.txt        # Python dependencies
├── ingestion_output/           # Validation reports directory
├── orders.csv                  # Source data file
├── run_validation.sh           # Quick validation script
├── VALIDATION_GUIDE.md         # Validation documentation
└── README.md                   # This file
```

## Configuration Options

### Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `aws_region` | AWS region | `us-east-1` | No |
| `vpc_cidr` | VPC CIDR block | `10.0.0.0/16` | No |
| `db_instance_class` | RDS instance type | `db.t3.micro` | No |
| `db_allocated_storage` | Storage in GB | `20` | No |
| `db_name` | Database name | `order_management` | No |
| `db_username` | Master username | `dbadmin` | No |
| `db_password` | Master password | - | **Yes** |

### Outputs

After deployment, Terraform provides:

```bash
terraform output rds_endpoint          # Full endpoint with port
terraform output rds_address           # Hostname only
terraform output database_name         # Database name
terraform output connection_string     # Connection string template
```

## Data Loading

The Python script (`scripts/load_orders_data.py`) handles:

- **Validation:** Checks row_id, order_id, discount range, date logic
- **Batch Processing:** Inserts 1000 records per batch using execute_values for optimal performance
- **Idempotency:** Skips loading if data already exists
- **Error Handling:** Logs invalid records but continues processing

### Manual Data Load

If you need to reload data:

```bash
# Set environment variables
export DB_HOST=$(cd terraform && terraform output -raw rds_address)
export DB_USER=dbadmin
export DB_PASSWORD='YourPassword'
export DB_NAME=order_management

# Run script
python3 scripts/load_orders_data.py
```

## Data Validation

After data loading, validate that the data was correctly ingested:

```bash
# Set environment variables (if not already set)
export DB_HOST=$(cd terraform && terraform output -raw rds_address)
export DB_USER=dbadmin
export DB_PASSWORD='YourPassword'
export DB_NAME=order_management
export CSV_FILE_PATH=orders.csv

# Run validation
python3 scripts/validate.py
```

### Validation Reports

The validation script generates comprehensive reports in the `ingestion_output/` folder:

1. **validation_report_TIMESTAMP.json** - Detailed JSON report with all metrics
2. **validation_report_TIMESTAMP.txt** - Human-readable text report
3. **validation_summary.txt** - Quick summary of last validation

### What Gets Validated

- **Row Count:** Compares total rows between CSV and database
- **Column Statistics:** Validates min, max, avg, sum for sales, profit, discount
- **Sample Data:** Shows first 5 records from both sources
- **Data Quality Issues:** Reports any statistical mismatches

### Sample Validation Output

```
================================================================================
VALIDATION SUMMARY
================================================================================
Status:       ✓ PASSED
CSV Rows:     9,994
DB Rows:      9,994
Issues:       0
Reports:      ingestion_output/
================================================================================
```

## Database Schema

### dev_orders.orders Table

| Column | Type | Constraints |
|--------|------|-------------|
| row_id | INTEGER | PRIMARY KEY |
| order_id | VARCHAR(50) | NOT NULL |
| order_date | DATE | |
| ship_date | DATE | |
| ship_mode | VARCHAR(50) | |
| customer_id | VARCHAR(50) | |
| customer_name | VARCHAR(100) | |
| segment | VARCHAR(50) | |
| country | VARCHAR(100) | |
| city | VARCHAR(100) | |
| state | VARCHAR(100) | |
| postal_code | VARCHAR(20) | |
| region | VARCHAR(50) | |
| product_id | VARCHAR(50) | |
| category | VARCHAR(50) | |
| sub_category | VARCHAR(50) | |
| product_name | VARCHAR(255) | |
| sales | DECIMAL(10,2) | |
| quantity | INTEGER | |
| discount | DECIMAL(5,2) | |
| profit | DECIMAL(10,4) | |

## Troubleshooting

### RDS Creation Fails

**Error:** Insufficient capacity or quota exceeded

**Solution:**
- Try a different region
- Use a different instance class
- Check AWS service quotas

### Database Connection Fails

**Error:** Connection timeout or refused

**Solution:**
```bash
# Verify RDS is available
aws rds describe-db-instances --db-instance-identifier orders-db

# Check security group allows your IP
# Update main.tf ingress rules if needed
```

### Data Load Fails

**Error:** CSV file not found

**Solution:**
```bash
# Ensure orders.csv is in project root
ls -la orders.csv

# Check Python script path in main.tf
```

**Error:** Invalid records

**Solution:**
- Check logs for specific validation errors
- Review CSV format (tab-separated, not comma)
- Verify date format is DD/MM/YY

### psql Command Not Found

**Solution:**
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql-client

# Verify installation
psql --version
```

## Cleanup

To destroy all resources:

```bash
cd terraform
terraform destroy
```

**Warning:** This will permanently delete:
- RDS instance and all data
- VPC and networking resources
- Security groups

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use AWS Secrets Manager** for production passwords
3. **Enable encryption at rest** (add `storage_encrypted = true`)
4. **Restrict security group** to specific IP ranges
5. **Enable automated backups** (set `backup_retention_period`)
6. **Use IAM authentication** instead of passwords when possible

## Cost Estimation

Approximate monthly costs (us-east-1):

- RDS db.t3.micro: ~$15/month
- Storage (20 GB): ~$2.30/month
- Data transfer: Minimal for development

**Total:** ~$17-20/month

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review Terraform logs: `terraform apply -debug`
3. Check Python script logs
4. Verify AWS service health

## License

This project is provided as-is for infrastructure automation purposes.
