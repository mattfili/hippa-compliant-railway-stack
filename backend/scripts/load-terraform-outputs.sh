#!/bin/sh
# ==============================================================================
# Load Terraform Outputs Script
# ==============================================================================
# Reads Terraform output JSON and exports environment variables for application
# ==============================================================================

TERRAFORM_OUTPUTS="/terraform/outputs.json"

if [ ! -f "$TERRAFORM_OUTPUTS" ]; then
  echo "ERROR: Terraform outputs file not found at $TERRAFORM_OUTPUTS"
  exit 1
fi

# Parse JSON and export environment variables
export RDS_ENDPOINT=$(jq -r '.rds_endpoint.value' "$TERRAFORM_OUTPUTS")
export RDS_READER_ENDPOINT=$(jq -r '.rds_reader_endpoint.value // ""' "$TERRAFORM_OUTPUTS")
export RDS_DB_NAME=$(jq -r '.rds_db_name.value' "$TERRAFORM_OUTPUTS")
export RDS_USERNAME=$(jq -r '.rds_username.value' "$TERRAFORM_OUTPUTS")

export S3_BUCKET_DOCUMENTS=$(jq -r '.s3_bucket_documents.value' "$TERRAFORM_OUTPUTS")
export S3_BUCKET_BACKUPS=$(jq -r '.s3_bucket_backups.value' "$TERRAFORM_OUTPUTS")
export S3_BUCKET_AUDIT_LOGS=$(jq -r '.s3_bucket_audit_logs.value' "$TERRAFORM_OUTPUTS")

export KMS_MASTER_KEY_ID=$(jq -r '.kms_master_key_id.value' "$TERRAFORM_OUTPUTS")
export KMS_MASTER_KEY_ARN=$(jq -r '.kms_master_key_arn.value' "$TERRAFORM_OUTPUTS")

export VPC_ID=$(jq -r '.vpc_id.value' "$TERRAFORM_OUTPUTS")
export APP_IAM_ROLE_ARN=$(jq -r '.app_iam_role_arn.value' "$TERRAFORM_OUTPUTS")
export AWS_REGION=$(jq -r '.aws_region.value' "$TERRAFORM_OUTPUTS")

# Construct DATABASE_URL from RDS outputs
# Assumes RDS_PASSWORD is provided via Railway environment variable
export DATABASE_URL="postgresql+asyncpg://${RDS_USERNAME}:${RDS_PASSWORD}@${RDS_ENDPOINT}/${RDS_DB_NAME}"

echo "Terraform outputs loaded:"
echo "  - RDS Endpoint: $RDS_ENDPOINT"
echo "  - S3 Documents Bucket: $S3_BUCKET_DOCUMENTS"
echo "  - KMS Master Key: $KMS_MASTER_KEY_ID"
echo "  - VPC ID: $VPC_ID"
