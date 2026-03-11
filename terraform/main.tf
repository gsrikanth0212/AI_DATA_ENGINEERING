terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.21"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC Configuration
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "rds-order-management-vpc"
  }
}

# Internet Gateway for public access
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "rds-igw"
  }
}

# Route Table
resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "rds-route-table"
  }
}

# Route Table Association for Subnet A
resource "aws_route_table_association" "subnet_a" {
  subnet_id      = aws_subnet.subnet_a.id
  route_table_id = aws_route_table.main.id
}

# Route Table Association for Subnet B
resource "aws_route_table_association" "subnet_b" {
  subnet_id      = aws_subnet.subnet_b.id
  route_table_id = aws_route_table.main.id
}

# Subnet A
resource "aws_subnet" "subnet_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.subnet_a_cidr
  availability_zone       = var.availability_zone_a
  map_public_ip_on_launch = true

  tags = {
    Name = "rds-subnet-a"
  }
}

# Subnet B
resource "aws_subnet" "subnet_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.subnet_b_cidr
  availability_zone       = var.availability_zone_b
  map_public_ip_on_launch = true

  tags = {
    Name = "rds-subnet-b"
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "rds_subnet" {
  name       = "rds-order-management-subnet-group"
  subnet_ids = [aws_subnet.subnet_a.id, aws_subnet.subnet_b.id]

  tags = {
    Name = "RDS Order Management Subnet Group"
  }
}

# Security Group for RDS
resource "aws_security_group" "rds_sg" {
  name        = "rds-order-management-sg"
  description = "Security group for RDS PostgreSQL instance"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "PostgreSQL access from anywhere (development only)"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "rds-order-management-sg"
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "orders_db" {
  identifier             = var.db_identifier
  engine                 = "postgres"
  engine_version         = var.db_engine_version
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage
  storage_type           = "gp2"
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  skip_final_snapshot    = true
  publicly_accessible    = true

  tags = {
    Name = "orders-database"
  }
}

# PostgreSQL Provider Configuration
provider "postgresql" {
  host     = aws_db_instance.orders_db.address
  port     = 5432
  database = var.db_name
  username = var.db_username
  password = var.db_password
  sslmode  = "require"
}

# Create dev_orders schema
resource "postgresql_schema" "dev_orders" {
  name     = "dev_orders"
  database = var.db_name

  depends_on = [aws_db_instance.orders_db]
}

# Create orders table using Python script
resource "null_resource" "create_orders_table" {
  provisioner "local-exec" {
    command     = "python3 ../scripts/create_table.py"
    working_dir = path.module

    environment = {
      DB_HOST     = aws_db_instance.orders_db.address
      DB_PORT     = "5432"
      DB_NAME     = var.db_name
      DB_USER     = var.db_username
      DB_PASSWORD = var.db_password
    }
  }

  depends_on = [postgresql_schema.dev_orders]
}

# Load data using Python script
resource "null_resource" "load_orders_data" {
  provisioner "local-exec" {
    command     = "python3 ../scripts/load_orders_data.py"
    working_dir = path.module

    environment = {
      DB_HOST      = aws_db_instance.orders_db.address
      DB_PORT      = "5432"
      DB_NAME      = var.db_name
      DB_USER      = var.db_username
      DB_PASSWORD  = var.db_password
      CSV_FILE_PATH = "../orders.csv"
    }
  }

  depends_on = [null_resource.create_orders_table]
}
