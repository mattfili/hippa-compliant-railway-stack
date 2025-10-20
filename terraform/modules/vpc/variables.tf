variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "CIDR block for VPC"
}

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

variable "availability_zones" {
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
  description = "Availability zones for multi-AZ deployment"
}

variable "enable_nat_gateway" {
  type        = bool
  default     = true
  description = "Enable NAT gateway for private subnet internet access"
}

variable "enable_vpc_endpoints" {
  type        = bool
  default     = true
  description = "Enable VPC endpoints for S3, RDS, Bedrock"
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Additional resource tags"
}
