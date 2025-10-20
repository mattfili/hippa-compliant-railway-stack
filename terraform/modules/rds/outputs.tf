# RDS Module - Output Values

# ==============================================================================
# Primary Instance Outputs
# ==============================================================================

output "rds_endpoint" {
  value       = aws_db_instance.main.endpoint
  description = "RDS primary endpoint (host:port)"
}

output "rds_address" {
  value       = aws_db_instance.main.address
  description = "RDS primary instance hostname"
}

output "rds_port" {
  value       = aws_db_instance.main.port
  description = "RDS primary instance port"
}

output "rds_db_name" {
  value       = aws_db_instance.main.db_name
  description = "Database name"
}

output "rds_username" {
  value       = aws_db_instance.main.username
  description = "Database master username"
  sensitive   = true
}

output "rds_password" {
  value       = random_password.master_password.result
  description = "Database master password"
  sensitive   = true
}

output "rds_arn" {
  value       = aws_db_instance.main.arn
  description = "RDS instance ARN"
}

output "rds_id" {
  value       = aws_db_instance.main.id
  description = "RDS instance identifier"
}

output "rds_resource_id" {
  value       = aws_db_instance.main.resource_id
  description = "RDS instance resource ID"
}

# ==============================================================================
# Read Replica Outputs
# ==============================================================================

output "rds_reader_endpoint" {
  value       = var.enable_read_replica ? aws_db_instance.read_replica[0].endpoint : ""
  description = "RDS reader endpoint (read replica)"
}

output "rds_reader_address" {
  value       = var.enable_read_replica ? aws_db_instance.read_replica[0].address : ""
  description = "RDS read replica hostname"
}

output "rds_reader_arn" {
  value       = var.enable_read_replica ? aws_db_instance.read_replica[0].arn : ""
  description = "RDS read replica ARN"
}

# ==============================================================================
# Subnet and Parameter Group Outputs
# ==============================================================================

output "db_subnet_group_name" {
  value       = aws_db_subnet_group.main.name
  description = "DB subnet group name"
}

output "db_subnet_group_arn" {
  value       = aws_db_subnet_group.main.arn
  description = "DB subnet group ARN"
}

output "db_parameter_group_name" {
  value       = aws_db_parameter_group.main.name
  description = "DB parameter group name"
}

output "db_parameter_group_arn" {
  value       = aws_db_parameter_group.main.arn
  description = "DB parameter group ARN"
}

# ==============================================================================
# Connection String Outputs
# ==============================================================================

output "connection_string" {
  value       = "postgresql://${aws_db_instance.main.username}:${random_password.master_password.result}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
  description = "Full PostgreSQL connection string for the primary instance"
  sensitive   = true
}

output "connection_string_asyncpg" {
  value       = "postgresql+asyncpg://${aws_db_instance.main.username}:${random_password.master_password.result}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
  description = "PostgreSQL connection string with asyncpg driver for Python"
  sensitive   = true
}

# ==============================================================================
# Monitoring Outputs
# ==============================================================================

output "monitoring_role_arn" {
  value       = var.enable_enhanced_monitoring && var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : ""
  description = "ARN of the IAM role for Enhanced Monitoring"
}

output "performance_insights_enabled" {
  value       = var.enable_performance_insights
  description = "Whether Performance Insights is enabled"
}

# ==============================================================================
# Metadata Outputs
# ==============================================================================

output "environment" {
  value       = var.environment
  description = "Environment name"
}

output "engine_version" {
  value       = aws_db_instance.main.engine_version_actual
  description = "Actual PostgreSQL engine version"
}

output "storage_encrypted" {
  value       = aws_db_instance.main.storage_encrypted
  description = "Whether storage encryption is enabled"
}

output "multi_az" {
  value       = aws_db_instance.main.multi_az
  description = "Whether Multi-AZ is enabled"
}
