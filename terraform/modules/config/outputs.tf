# ==============================================================================
# AWS Config Module - Output Values
# ==============================================================================

output "config_recorder_name" {
  value       = aws_config_configuration_recorder.main.name
  description = "Name of the AWS Config configuration recorder"
}

output "config_recorder_role_arn" {
  value       = aws_iam_role.config.arn
  description = "ARN of the IAM role used by AWS Config"
}

output "config_sns_topic_arn" {
  value       = aws_sns_topic.config_alerts.arn
  description = "ARN of the SNS topic for Config compliance alerts"
}

output "config_delivery_channel_name" {
  value       = aws_config_delivery_channel.main.name
  description = "Name of the AWS Config delivery channel"
}

output "config_rules" {
  value = {
    s3_encryption         = aws_config_config_rule.s3_bucket_encryption.name
    rds_encryption        = aws_config_config_rule.rds_storage_encrypted.name
    rds_public_access     = aws_config_config_rule.rds_public_access.name
    iam_no_admin_access   = aws_config_config_rule.iam_policy_no_admin_access.name
    cloudtrail_enabled    = aws_config_config_rule.cloudtrail_enabled.name
    vpc_sg_authorized     = aws_config_config_rule.vpc_sg_authorized_ports.name
  }
  description = "Map of AWS Config rule names for HIPAA compliance monitoring"
}
