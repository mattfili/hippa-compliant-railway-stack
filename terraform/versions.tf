# ==============================================================================
# Terraform Version and Provider Configuration
# ==============================================================================
# Defines required Terraform version and AWS provider configuration
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ------------------------------------------------------------------------------
# AWS Provider Configuration
# ------------------------------------------------------------------------------

provider "aws" {
  region = var.aws_region

  # Default tags applied to all AWS resources
  default_tags {
    tags = {
      ManagedBy = "Terraform"
      Project   = "HIPAA-Compliant-Document-Management"
    }
  }
}
