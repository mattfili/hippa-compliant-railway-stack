# ==============================================================================
# Root Terraform Outputs
# ==============================================================================
# Output values for Railway integration and application configuration
# These outputs are exported to JSON for consumption by the backend application
# ==============================================================================

# ------------------------------------------------------------------------------
# Database Outputs
# ------------------------------------------------------------------------------

output "rds_endpoint" {
  value       = module.rds.rds_endpoint
  description = "RDS primary endpoint (host:port) for database connections"
}

output "rds_reader_endpoint" {
  value       = module.rds.rds_reader_endpoint
  description = "RDS reader endpoint for read replica (empty if no replica)"
}

output "rds_db_name" {
  value       = module.rds.rds_db_name
  description = "Database name"
}

output "rds_username" {
  value       = module.rds.rds_username
  description = "Database master username"
  sensitive   = true
}

output "rds_arn" {
  value       = module.rds.rds_arn
  description = "RDS instance ARN for IAM authentication and monitoring"
}

# ------------------------------------------------------------------------------
# S3 Storage Outputs
# ------------------------------------------------------------------------------

output "s3_bucket_documents" {
  value       = module.s3.s3_bucket_documents
  description = "Documents bucket name for PHI document storage"
}

output "s3_bucket_backups" {
  value       = module.s3.s3_bucket_backups
  description = "Backups bucket name for database and application backups"
}

output "s3_bucket_audit_logs" {
  value       = module.s3.s3_bucket_audit_logs
  description = "Audit logs bucket name for compliance logging"
}

output "s3_bucket_documents_arn" {
  value       = module.s3.s3_bucket_documents_arn
  description = "Documents bucket ARN for IAM policy references"
}

# ------------------------------------------------------------------------------
# KMS Encryption Outputs
# ------------------------------------------------------------------------------

output "kms_master_key_id" {
  value       = module.kms.kms_master_key_id
  description = "KMS master key ID for infrastructure encryption"
}

output "kms_master_key_arn" {
  value       = module.kms.kms_master_key_arn
  description = "KMS master key ARN for policy references"
}

# ------------------------------------------------------------------------------
# VPC Networking Outputs
# ------------------------------------------------------------------------------

output "vpc_id" {
  value       = module.vpc.vpc_id
  description = "VPC ID for network configuration"
}

output "vpc_endpoint_s3" {
  value       = module.vpc.vpc_endpoint_s3_id
  description = "S3 VPC endpoint ID for private S3 access"
}

output "vpc_endpoint_rds" {
  value       = module.vpc.vpc_endpoint_rds_id
  description = "RDS VPC endpoint ID for private RDS access"
}

output "vpc_endpoint_bedrock" {
  value       = module.vpc.vpc_endpoint_bedrock_id
  description = "Bedrock VPC endpoint ID for private Bedrock API access"
}

output "private_subnet_ids" {
  value       = module.vpc.private_subnet_ids
  description = "Private subnet IDs for RDS and application resources"
}

output "public_subnet_ids" {
  value       = module.vpc.public_subnet_ids
  description = "Public subnet IDs for NAT gateways"
}

# ------------------------------------------------------------------------------
# IAM Access Outputs
# ------------------------------------------------------------------------------

output "app_iam_role_arn" {
  value       = module.iam.app_iam_role_arn
  description = "Backend application IAM role ARN for Railway assumption"
}

output "app_iam_role_name" {
  value       = module.iam.app_iam_role_name
  description = "Backend application IAM role name"
}

# ------------------------------------------------------------------------------
# AWS Config Outputs
# ------------------------------------------------------------------------------

output "config_recorder_name" {
  value       = module.config.config_recorder_name
  description = "AWS Config recorder name for compliance monitoring"
}

output "config_sns_topic_arn" {
  value       = module.config.config_sns_topic_arn
  description = "SNS topic ARN for Config compliance alerts"
}

# ------------------------------------------------------------------------------
# Environment Metadata
# ------------------------------------------------------------------------------

output "aws_region" {
  value       = local.aws_region
  description = "AWS region where resources are deployed"
}

output "aws_account_id" {
  value       = local.aws_account_id
  description = "AWS account ID"
  sensitive   = true
}

output "environment" {
  value       = var.environment
  description = "Environment name (dev, staging, production)"
}

output "terraform_workspace" {
  value       = terraform.workspace
  description = "Terraform workspace used for deployment"
}
