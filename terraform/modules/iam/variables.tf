# ==============================================================================
# IAM Module - Input Variables
# ==============================================================================

variable "environment" {
  type        = string
  description = "Deployment tier (dev, staging, production)"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of dev, staging, production."
  }
}

variable "name_suffix" {
  type        = string
  default     = ""
  description = "Optional suffix for resource names (tests/ephemeral runs)"

  validation {
    condition     = can(regex("^[a-z0-9-]*$", var.name_suffix))
    error_message = "name_suffix may contain only lowercase letters, digits, and hyphens."
  }
}

variable "s3_bucket_documents_arn" {
  type        = string
  description = "ARN of the S3 bucket for PHI document storage"

  validation {
    condition     = can(regex("^arn:aws:s3:::.+$", var.s3_bucket_documents_arn))
    error_message = "Must be a valid S3 bucket ARN"
  }
}

variable "s3_bucket_backups_arn" {
  type        = string
  description = "ARN of the S3 bucket for database and application backups"

  validation {
    condition     = can(regex("^arn:aws:s3:::.+$", var.s3_bucket_backups_arn))
    error_message = "Must be a valid S3 bucket ARN"
  }
}

variable "s3_bucket_audit_logs_arn" {
  type        = string
  description = "ARN of the S3 bucket for audit logs and compliance trail"

  validation {
    condition     = can(regex("^arn:aws:s3:::.+$", var.s3_bucket_audit_logs_arn))
    error_message = "Must be a valid S3 bucket ARN"
  }
}

variable "kms_master_key_arn" {
  type        = string
  description = "ARN of the KMS master key for infrastructure encryption"

  validation {
    condition     = can(regex("^arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/.+$", var.kms_master_key_arn))
    error_message = "Must be a valid KMS key ARN"
  }
}

variable "external_id" {
  type        = string
  description = "External ID for AssumeRole trust policy (for Railway or external access)"
  default     = "railway-hipaa-app"
  sensitive   = true
}

variable "enable_rds_monitoring" {
  type        = bool
  description = "Enable IAM role for RDS Enhanced Monitoring"
  default     = false
}

variable "tags" {
  type        = map(string)
  description = "Additional resource tags"
  default     = {}
}
