# ==============================================================================
# Terraform Backend Configuration
# ==============================================================================
# Configures S3 backend for remote state storage with DynamoDB locking
# This file requires manual bootstrapping before first terraform init
# ==============================================================================

# IMPORTANT: Before running terraform init, you must:
# 1. Create S3 bucket: terraform-state-{environment}-{account-id}
# 2. Enable versioning on the S3 bucket
# 3. Create DynamoDB table: terraform-state-lock with primary key "LockID" (String)
# 4. Update the bucket name below with your actual account ID

# Example AWS CLI commands for bootstrapping:
# aws s3api create-bucket --bucket terraform-state-dev-873125487926 --region us-east-1
# aws s3api put-bucket-versioning --bucket terraform-state-dev-873125487926 --versioning-configuration Status=Enabled
# aws dynamodb create-table --table-name terraform-state-lock --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST --region us-east-1

terraform {
  backend "s3" {
    # S3 bucket for state storage
    # Replace {account-id} with your AWS account ID
    bucket = "terraform-state-dev-873125487926"

    # State file key - includes workspace for environment isolation
    key = "hipaa-infrastructure/terraform.tfstate"

    # AWS region for state bucket
    region = "us-east-1"

    # DynamoDB table for state locking
    dynamodb_table = "terraform-state-lock"

    # Enable encryption at rest for state file
    encrypt = true

    # Enable workspace support for multi-environment deployments
    workspace_key_prefix = "workspaces"

    # Prevent concurrent modifications
    skip_credentials_validation = false
    skip_metadata_api_check     = false
    skip_region_validation      = false
  }
}

# NOTE: The backend configuration does not support interpolation or variables
# You must manually update the bucket name with your actual AWS account ID
# Alternatively, use the -backend-config flag during terraform init:
#
# terraform init \
#   -backend-config="bucket=terraform-state-dev-873125487926" \
#   -backend-config="region=us-east-1" \
#   -backend-config="dynamodb_table=terraform-state-lock"
