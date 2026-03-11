output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.orders_db.endpoint
}

output "rds_address" {
  description = "RDS instance address (hostname only)"
  value       = aws_db_instance.orders_db.address
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.orders_db.db_name
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "subnet_ids" {
  description = "Subnet IDs"
  value       = [aws_subnet.subnet_a.id, aws_subnet.subnet_b.id]
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.rds_sg.id
}

output "connection_string" {
  description = "PostgreSQL connection string (without password)"
  value       = "postgresql://${var.db_username}@${aws_db_instance.orders_db.address}:5432/${var.db_name}"
  sensitive   = false
}
