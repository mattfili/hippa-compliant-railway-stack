# ==============================================================================
# KMS Module - Output Values
# ==============================================================================

output "kms_master_key_id" {
  value       = aws_kms_key.master.key_id
  description = "KMS master key ID (UUID format) for resource encryption configuration"
}

output "kms_master_key_arn" {
  value       = aws_kms_key.master.arn
  description = "KMS master key ARN (full Amazon Resource Name) for IAM policy configuration"
}

output "kms_key_alias" {
  value       = aws_kms_alias.master.name
  description = "KMS key alias name for easier reference in application code"
}
