# ==============================================================================
# Security Groups Module - Input Variables
# ==============================================================================
# Variables for configuring security groups with least-privilege access rules
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

variable "vpc_id" {
  type        = string
  description = "VPC ID where security groups will be created (required from VPC module)"

  validation {
    condition     = can(regex("^vpc-[a-z0-9]+$", var.vpc_id))
    error_message = "VPC ID must be a valid AWS VPC identifier (vpc-xxxxx)"
  }
}

variable "railway_ip_ranges" {
  type        = list(string)
  description = <<-EOT
    List of Railway IP ranges for inbound HTTPS access to application.
    If empty, no ingress rules will be created for Railway access.
    Obtain Railway IP ranges from Railway documentation or support.
    Example: ["192.0.2.0/24", "198.51.100.0/24"]
  EOT
  default     = []

  validation {
    condition = alltrue([
      for cidr in var.railway_ip_ranges :
      can(cidrhost(cidr, 0))
    ])
    error_message = "All Railway IP ranges must be valid CIDR blocks"
  }
}

variable "tags" {
  type        = map(string)
  description = "Additional resource tags to apply to all security groups"
  default     = {}
}
