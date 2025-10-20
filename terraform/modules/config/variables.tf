# ==============================================================================
# AWS Config Module - Input Variables
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

variable "s3_bucket_audit_logs" {
  type        = string
  description = "S3 bucket name for AWS Config snapshots and configuration history"
}

variable "sns_alert_email" {
  type        = string
  description = "Email address for Config rule violation alerts (optional)"
  default     = ""
}

variable "enable_auto_remediation" {
  type        = bool
  description = "Enable automatic remediation for Config rule violations (disabled by default for safety)"
  default     = false
}

variable "tags" {
  type        = map(string)
  description = "Additional resource tags to apply to all Config resources"
  default     = {}
}
