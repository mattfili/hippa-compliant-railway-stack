# ==============================================================================
# IAM Module - Output Values
# ==============================================================================

output "app_iam_role_arn" {
  value       = aws_iam_role.backend_app.arn
  description = "ARN of the backend application IAM role"
}

output "app_iam_role_name" {
  value       = aws_iam_role.backend_app.name
  description = "Name of the backend application IAM role"
}

output "rds_monitoring_role_arn" {
  value       = var.enable_rds_monitoring ? aws_iam_role.rds_monitoring[0].arn : ""
  description = "ARN of the RDS Enhanced Monitoring role (if enabled)"
}

output "s3_policy_arn" {
  value       = aws_iam_policy.s3_access.arn
  description = "ARN of the S3 access policy"
}

output "kms_policy_arn" {
  value       = aws_iam_policy.kms_access.arn
  description = "ARN of the KMS access policy"
}

output "bedrock_policy_arn" {
  value       = aws_iam_policy.bedrock_access.arn
  description = "ARN of the Bedrock access policy"
}
