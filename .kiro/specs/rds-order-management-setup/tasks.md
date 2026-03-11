# Implementation Plan: RDS Order Management Setup

## Overview

This implementation creates AWS RDS PostgreSQL infrastructure using Terraform, including VPC networking, security groups, RDS instance provisioning, database schema setup, and automated data loading from a CSV file. The implementation follows a sequential approach: infrastructure first, then database objects, then data loading with Python.

## Tasks

- [x] 1. Set up Terraform project structure and provider configuration
  - Create main.tf, variables.tf, and outputs.tf files
  - Configure AWS provider with region settings
  - Configure PostgreSQL provider for database operations
  - Define required Terraform version and provider versions
  - _Requirements: 9.1, 9.2, 9.3_

- [x] 2. Implement VPC and network infrastructure
  - [x] 2.1 Create VPC with DNS support enabled
    - Define VPC resource with CIDR block 10.0.0.0/16
    - Enable DNS hostnames and DNS support
    - _Requirements: 1.1, 1.2_
  
  - [x] 2.2 Create subnets in multiple availability zones
    - Create at least 2 subnets in different AZs
    - Assign CIDR blocks within VPC range (10.0.1.0/24, 10.0.2.0/24)
    - _Requirements: 1.3, 1.4_
  
  - [x] 2.3 Create DB subnet group
    - Define DB subnet group resource containing all subnet IDs
    - _Requirements: 1.5, 9.2_
  
  - [ ]* 2.4 Write property test for subnet CIDR containment
    - **Property 2: Subnet CIDR Containment**
    - **Validates: Requirements 1.4**

- [x] 3. Implement security group configuration
  - [x] 3.1 Create security group for RDS access
    - Create security group attached to VPC
    - Add ingress rule for PostgreSQL port 5432
    - Restrict access to specified CIDR blocks
    - Add egress rule for outbound traffic
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 9.1_
  
  - [ ]* 3.2 Write property test for security group CIDR restriction
    - **Property 4: Security Group CIDR Restriction**
    - **Validates: Requirements 2.3**

- [x] 4. Provision RDS PostgreSQL instance
  - [x] 4.1 Create RDS instance resource
    - Configure engine as "postgres" with version 15.4
    - Set instance class to db.t3.micro
    - Allocate 20 GB storage (gp2)
    - Create initial database "order_management"
    - Set publicly_accessible to false
    - Attach security group and DB subnet group
    - Configure master credentials using variables
    - Enable skip_final_snapshot for development
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 9.3, 11.1, 11.2_
  
  - [ ]* 4.2 Write property test for storage minimum threshold
    - **Property 6: Storage Minimum Threshold**
    - **Validates: Requirements 3.3**

- [ ] 5. Checkpoint - Verify infrastructure provisioning
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement database schema creation
  - [x] 6.1 Create dev_orders schema using PostgreSQL provider
    - Define postgresql_schema resource for "dev_orders"
    - Use CREATE SCHEMA IF NOT EXISTS for idempotency
    - Add dependency on RDS instance availability
    - _Requirements: 4.1, 4.2, 4.3, 9.4_
  
  - [ ]* 6.2 Write property test for database object idempotency
    - **Property 8: Database Object Idempotency**
    - **Validates: Requirements 4.3, 8.2_

- [x] 7. Implement orders table creation
  - [x] 7.1 Create orders table with complete schema
    - Define postgresql_table resource or use null_resource with SQL
    - Create table in dev_orders schema with all 21 columns
    - Define row_id as INTEGER PRIMARY KEY
    - Define order_id as VARCHAR(50) NOT NULL
    - Define sales and profit as DECIMAL types
    - Define order_date and ship_date as DATE types
    - Use CREATE TABLE IF NOT EXISTS for idempotency
    - Add dependency on schema creation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 9.5_
  
  - [ ]* 7.2 Write unit tests for table schema validation
    - Test table exists in information_schema
    - Test column definitions match requirements
    - _Requirements: 5.7_

- [x] 8. Implement Python data loading script
  - [x] 8.1 Create Python script for CSV data loading
    - Create load_orders_data.py script
    - Implement database connection using psycopg2
    - Implement check for existing data (skip if table has rows)
    - Implement CSV file reading with tab-separated parsing
    - Implement record validation logic (row_id, order_id, discount, dates)
    - Implement batch insert with 1000 records per batch
    - Implement error logging for invalid records
    - Implement row count verification after load
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 7.1, 7.2, 7.3, 7.4, 7.5, 9.6_
  
  - [ ]* 8.2 Write property test for CSV parsing consistency
    - **Property 10: CSV Parsing Consistency**
    - **Validates: Requirements 6.4**
  
  - [ ]* 8.3 Write property test for discount range validation
    - **Property 14: Discount Range Validation**
    - **Validates: Requirements 7.3**
  
  - [ ]* 8.4 Write property test for date logic validation
    - **Property 15: Date Logic Validation**
    - **Validates: Requirements 7.4**

- [x] 9. Integrate data loading with Terraform
  - [x] 9.1 Create null_resource with local-exec provisioner
    - Define null_resource to execute Python script
    - Pass database connection parameters as environment variables
    - Add dependency on table creation
    - Handle sensitive credentials properly
    - _Requirements: 9.6, 11.3_
  
  - [ ]* 9.2 Write property test for data load idempotency
    - **Property 9: Data Load Idempotency**
    - **Validates: Requirements 6.2, 8.4**

- [x] 10. Implement Terraform variables and outputs
  - [x] 10.1 Define input variables
    - Create variables for AWS region, instance class, storage size
    - Create sensitive variable for master password
    - Define validation rules for variables
    - _Requirements: 11.1_
  
  - [x] 10.2 Define output values
    - Output RDS endpoint address in "host:port" format
    - Output database name
    - Mark sensitive outputs appropriately
    - _Requirements: 15.1, 15.2, 15.3, 15.4_

- [x] 11. Implement error handling and state management
  - [x] 11.1 Add error handling to Python script
    - Handle database connection failures
    - Handle CSV file not found errors
    - Handle batch insert failures with rollback
    - Handle permission denied errors
    - _Requirements: 10.2, 10.3, 10.4, 10.5_
  
  - [x] 11.2 Configure Terraform state management
    - Ensure state file records all resource IDs
    - Mark sensitive values in state
    - _Requirements: 11.2, 14.1_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Create documentation and usage instructions
  - [x] 13.1 Create README.md with setup instructions
    - Document prerequisites (Terraform, Python, psycopg2, orders.csv)
    - Document variable configuration
    - Document execution steps (terraform init, plan, apply)
    - Document connection instructions
    - _Requirements: 15.1, 15.2_
  
  - [x] 13.2 Create requirements.txt for Python dependencies
    - List psycopg2-binary for PostgreSQL connectivity
    - _Requirements: 6.3_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The implementation uses Terraform for infrastructure and Python for data loading
- All database credentials should be passed as Terraform variables, never hardcoded
- The orders.csv file must exist in the working directory before running terraform apply
- Property tests validate universal correctness properties across all executions
- Checkpoints ensure incremental validation and allow for user feedback
