# ==============================================================================
# Security Groups Module - Outputs
# ==============================================================================
# Exports security group IDs for use by dependent modules (RDS, VPC endpoints)
# ==============================================================================

output "rds_security_group_id" {
  value       = aws_security_group.rds.id
  description = "Security group ID for RDS PostgreSQL database - allows PostgreSQL (5432) from application only"
}

output "app_security_group_id" {
  value       = aws_security_group.app.id
  description = "Security group ID for backend application - allows HTTPS from Railway, PostgreSQL to RDS, HTTPS to VPC endpoints"
}

output "vpc_endpoint_security_group_id" {
  value       = aws_security_group.vpc_endpoints.id
  description = "Security group ID for VPC interface endpoints - allows HTTPS from application for S3, Bedrock access"
}
