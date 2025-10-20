# ==============================================================================
# TFLint Configuration for HIPAA-Compliant Infrastructure
# ==============================================================================
# This configuration enforces AWS best practices and HIPAA compliance
# requirements for Terraform code quality and security
# ==============================================================================

plugin "terraform" {
  enabled = true
  version = "0.5.0"
  source  = "github.com/terraform-linters/tflint-ruleset-terraform"
}

plugin "aws" {
  enabled = true
  version = "0.29.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

# ==============================================================================
# Terraform Language Rules
# ==============================================================================

rule "terraform_deprecated_interpolation" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_naming_convention" {
  enabled = true
  format  = "snake_case"
}

rule "terraform_required_providers" {
  enabled = true
}

rule "terraform_required_version" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}

rule "terraform_unused_declarations" {
  enabled = true
}

# ==============================================================================
# AWS Security Rules - HIPAA Compliance
# ==============================================================================

# Enforce encryption on all S3 buckets
rule "aws_s3_bucket_default_encryption" {
  enabled = true
}

# Block public access to S3 buckets
rule "aws_s3_bucket_public_access_block" {
  enabled = true
}

# Ensure S3 bucket versioning is enabled
rule "aws_s3_bucket_versioning" {
  enabled = true
}

# Ensure RDS instances are encrypted
rule "aws_db_instance_encryption_at_rest" {
  enabled = true
}

# Prevent public RDS instances
rule "aws_db_instance_publicly_accessible" {
  enabled = true
}

# Enforce KMS key rotation
rule "aws_kms_key_rotation_enabled" {
  enabled = true
}

# Ensure security groups don't allow unrestricted ingress
rule "aws_security_group_unrestricted_ingress" {
  enabled = true
}

# Prevent overly permissive IAM policies
rule "aws_iam_policy_wildcards" {
  enabled = true
}

# ==============================================================================
# AWS Resource Validation Rules
# ==============================================================================

# Validate resource naming conventions
rule "aws_resource_missing_tags" {
  enabled = true
  tags = ["Name", "Environment", "ManagedBy"]
}

# Ensure VPC resources follow best practices
rule "aws_vpc_flow_logs_enabled" {
  enabled = false  # Not implemented in initial version (Feature 10)
}

# Validate CloudWatch log retention
rule "aws_cloudwatch_log_group_retention" {
  enabled = true
}

# ==============================================================================
# Performance and Cost Optimization
# ==============================================================================

# Warn about expensive instance types in non-production
rule "aws_instance_type" {
  enabled = false  # Allow flexibility for environment-specific sizing
}

# Warn about unused resources
rule "aws_resource_unused" {
  enabled = true
}

# ==============================================================================
# Configuration
# ==============================================================================

config {
  # Force download of modules before linting
  module = true

  # Enable deep checking (slower but more thorough)
  deep_check = false

  # Disable default rules that conflict with our setup
  disabled_by_default = false

  # Only show issues for the current directory
  varfile = []
}
