# ==============================================================================
# S3 Module - Output Values
# ==============================================================================

output "s3_bucket_documents" {
  value       = aws_s3_bucket.documents.id
  description = "Documents bucket name for PHI document storage"
}

output "s3_bucket_backups" {
  value       = aws_s3_bucket.backups.id
  description = "Backups bucket name for database and application backups"
}

output "s3_bucket_audit_logs" {
  value       = aws_s3_bucket.audit_logs.id
  description = "Audit logs bucket name for compliance and access logging"
}

output "s3_bucket_documents_arn" {
  value       = aws_s3_bucket.documents.arn
  description = "Documents bucket ARN for IAM policy configuration"
}

output "s3_bucket_backups_arn" {
  value       = aws_s3_bucket.backups.arn
  description = "Backups bucket ARN for IAM policy configuration"
}

output "s3_bucket_audit_logs_arn" {
  value       = aws_s3_bucket.audit_logs.arn
  description = "Audit logs bucket ARN for IAM policy configuration"
}

output "s3_bucket_documents_region" {
  value       = aws_s3_bucket.documents.region
  description = "Documents bucket region"
}
