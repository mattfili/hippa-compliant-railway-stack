# ==============================================================================
# KMS Module - Input Variables
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

variable "aws_account_id" {
  type        = string
  description = "AWS account ID for key policy configuration"

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "AWS account ID must be a 12-digit number"
  }
}

variable "enable_key_rotation" {
  type        = bool
  description = "Enable automatic key rotation (recommended for security compliance)"
  default     = true
}

variable "tags" {
  type        = map(string)
  description = "Additional resource tags to apply to KMS resources"
  default     = {}
}
