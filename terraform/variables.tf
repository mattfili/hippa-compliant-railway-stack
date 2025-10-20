# ==============================================================================
# Root Terraform Variables
# ==============================================================================
# Input variables for root configuration orchestrating all modules
# ==============================================================================

# ------------------------------------------------------------------------------
# Environment Configuration
# ------------------------------------------------------------------------------

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

variable "aws_region" {
  type        = string
  description = "AWS region for resource deployment"
  default     = "us-east-1"
}

# ------------------------------------------------------------------------------
# VPC Configuration
# ------------------------------------------------------------------------------

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for VPC"
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  type        = list(string)
  description = "Availability zones for multi-AZ deployment"
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "enable_nat_gateway" {
  type        = bool
  description = "Enable NAT gateway for private subnet internet access"
  default     = true
}

variable "enable_vpc_endpoints" {
  type        = bool
  description = "Enable VPC endpoints for S3, RDS, Bedrock"
  default     = true
}

# ------------------------------------------------------------------------------
# Networking Configuration
# ------------------------------------------------------------------------------

variable "railway_ip_ranges" {
  type        = list(string)
  description = "Railway IP ranges for inbound access to application security group"
  default     = []
  # Note: Populate from Railway documentation or use empty list for unrestricted access
  # Example: ["52.1.2.3/32", "52.4.5.6/32"]
}

# ------------------------------------------------------------------------------
# KMS Configuration
# ------------------------------------------------------------------------------

variable "enable_key_rotation" {
  type        = bool
  description = "Enable automatic KMS key rotation (365-day cycle)"
  default     = true
}

# ------------------------------------------------------------------------------
# S3 Configuration
# ------------------------------------------------------------------------------

variable "enable_lifecycle_policies" {
  type        = bool
  description = "Enable S3 lifecycle policies for cost optimization"
  default     = true
}

variable "documents_bucket_name" {
  type        = string
  description = "Override default documents bucket name (leave empty for auto-generated name)"
  default     = ""
}

# ------------------------------------------------------------------------------
# RDS Configuration
# ------------------------------------------------------------------------------

variable "rds_instance_class" {
  type        = string
  description = "RDS instance type (e.g., db.t3.medium, db.r6g.xlarge)"
  default     = "db.t3.medium"
}

variable "rds_allocated_storage" {
  type        = number
  description = "Allocated storage for RDS in GB"
  default     = 20

  validation {
    condition     = var.rds_allocated_storage >= 20 && var.rds_allocated_storage <= 65536
    error_message = "RDS allocated storage must be between 20 GB and 65536 GB"
  }
}

variable "rds_multi_az" {
  type        = bool
  description = "Enable Multi-AZ deployment for RDS (recommended for staging and production)"
  default     = false
}

variable "enable_read_replica" {
  type        = bool
  description = "Enable read replica for RDS (production only)"
  default     = false
}

variable "backup_retention_days" {
  type        = number
  description = "Automated backup retention period in days"
  default     = 30

  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 35
    error_message = "Backup retention days must be between 1 and 35"
  }
}

variable "deletion_protection" {
  type        = bool
  description = "Enable deletion protection for RDS (recommended for production)"
  default     = false
}

# ------------------------------------------------------------------------------
# AWS Config Configuration
# ------------------------------------------------------------------------------

variable "sns_alert_email" {
  type        = string
  description = "Email address for AWS Config compliance violation alerts (leave empty to skip email subscription)"
  default     = ""
}

variable "enable_auto_remediation" {
  type        = bool
  description = "Enable automatic remediation for Config rule violations (disabled by default for safety)"
  default     = false
}

# ------------------------------------------------------------------------------
# Common Tags
# ------------------------------------------------------------------------------

variable "tags" {
  type        = map(string)
  description = "Additional resource tags to apply to all resources"
  default     = {}
}
