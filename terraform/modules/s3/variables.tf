# ==============================================================================
# S3 Module - Input Variables
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
  description = "AWS account ID for unique bucket naming"

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "AWS account ID must be a 12-digit number"
  }
}

variable "kms_key_id" {
  type        = string
  description = "KMS key ID for S3 bucket encryption (SSE-KMS)"
}

variable "enable_lifecycle_policies" {
  type        = bool
  description = "Enable S3 lifecycle policies for cost optimization (transitions to IA and Glacier)"
  default     = true
}

variable "documents_bucket_name" {
  type        = string
  description = "Override default documents bucket name (optional, defaults to hipaa-compliant-docs-{environment}-{account-id})"
  default     = ""
}

variable "tags" {
  type        = map(string)
  description = "Additional resource tags to apply to all S3 buckets"
  default     = {}
}
