#!/bin/bash
set -e

# Bootstrap Terraform State Backend
# This script creates the S3 bucket and DynamoDB table required for Terraform remote state

echo "=========================================="
echo "Terraform State Backend Bootstrap"
echo "=========================================="
echo ""

# Check for required environment variables
if [ -z "$AWS_PROFILE" ]; then
    echo "ERROR: AWS_PROFILE environment variable not set"
    echo "Run: export AWS_PROFILE=terraform-test"
    exit 1
fi

if [ -z "$AWS_REGION" ]; then
    echo "ERROR: AWS_REGION environment variable not set"
    echo "Run: export AWS_REGION=us-east-1"
    exit 1
fi

# Get AWS account ID
echo "Getting AWS account ID..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile $AWS_PROFILE)

if [ -z "$ACCOUNT_ID" ]; then
    echo "ERROR: Could not retrieve AWS account ID"
    echo "Check your AWS credentials: aws sts get-caller-identity --profile $AWS_PROFILE"
    exit 1
fi

echo "✓ AWS Account ID: $ACCOUNT_ID"
echo "✓ AWS Region: $AWS_REGION"
echo "✓ AWS Profile: $AWS_PROFILE"
echo ""

# Fix backend.tf file first
echo "Fixing backend.tf configuration..."
SCRIPT_DIR="$(dirname "$0")"
if [ -f "$SCRIPT_DIR/fix-backend.sh" ]; then
    # Export variables for the fix script
    export AWS_PROFILE AWS_REGION ACCOUNT_ID
    bash "$SCRIPT_DIR/fix-backend.sh"
else
    echo "WARNING: fix-backend.sh not found, skipping backend.tf update"
fi
echo ""

# Define resource names
STATE_BUCKET="terraform-state-dev-${ACCOUNT_ID}"
LOCK_TABLE="terraform-state-lock"

# Create S3 bucket for state
echo "Creating S3 bucket for Terraform state..."
if aws s3 ls "s3://${STATE_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    if [ "$AWS_REGION" = "us-east-1" ]; then
        # us-east-1 doesn't need LocationConstraint
        aws s3api create-bucket \
            --bucket "${STATE_BUCKET}" \
            --profile $AWS_PROFILE \
            --region $AWS_REGION
    else
        # Other regions need LocationConstraint
        aws s3api create-bucket \
            --bucket "${STATE_BUCKET}" \
            --profile $AWS_PROFILE \
            --region $AWS_REGION \
            --create-bucket-configuration LocationConstraint=$AWS_REGION
    fi
    echo "✓ Created S3 bucket: ${STATE_BUCKET}"
else
    echo "✓ S3 bucket already exists: ${STATE_BUCKET}"
fi

# Enable versioning on state bucket
echo "Enabling versioning on state bucket..."
aws s3api put-bucket-versioning \
    --bucket "${STATE_BUCKET}" \
    --versioning-configuration Status=Enabled \
    --profile $AWS_PROFILE \
    --region $AWS_REGION
echo "✓ Versioning enabled on ${STATE_BUCKET}"

# Enable encryption on state bucket
echo "Enabling encryption on state bucket..."
aws s3api put-bucket-encryption \
    --bucket "${STATE_BUCKET}" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            },
            "BucketKeyEnabled": false
        }]
    }' \
    --profile $AWS_PROFILE \
    --region $AWS_REGION
echo "✓ Encryption enabled on ${STATE_BUCKET}"

# Block public access on state bucket
echo "Blocking public access on state bucket..."
aws s3api put-public-access-block \
    --bucket "${STATE_BUCKET}" \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true \
    --profile $AWS_PROFILE \
    --region $AWS_REGION
echo "✓ Public access blocked on ${STATE_BUCKET}"

# Create DynamoDB table for state locking
echo "Creating DynamoDB table for state locking..."
if aws dynamodb describe-table --table-name "${LOCK_TABLE}" --profile $AWS_PROFILE --region $AWS_REGION 2>&1 | grep -q 'ResourceNotFoundException'; then
    aws dynamodb create-table \
        --table-name "${LOCK_TABLE}" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --tags Key=Environment,Value=dev Key=ManagedBy,Value=Terraform

    echo "Waiting for DynamoDB table to become active..."
    aws dynamodb wait table-exists \
        --table-name "${LOCK_TABLE}" \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    echo "✓ Created DynamoDB table: ${LOCK_TABLE}"
else
    echo "✓ DynamoDB table already exists: ${LOCK_TABLE}"
fi

# Update backend.tf with actual values
BACKEND_FILE="../backend.tf"
if [ -f "$BACKEND_FILE" ]; then
    echo ""
    echo "Updating backend.tf with bootstrap values..."

    # Create a backup
    cp "$BACKEND_FILE" "${BACKEND_FILE}.backup"

    # Update placeholder values (if they exist)
    sed -i.tmp "s/terraform-state-{environment}-{account-id}/terraform-state-dev-${ACCOUNT_ID}/g" "$BACKEND_FILE"
    rm -f "${BACKEND_FILE}.tmp"

    echo "✓ Updated backend.tf (backup saved as backend.tf.backup)"
fi

echo ""
echo "=========================================="
echo "✓ State backend bootstrap complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. cd /Users/mattfili/Dev/hippa-compliant-railway-stack/terraform"
echo "2. terraform init"
echo "3. terraform workspace new dev"
echo "4. terraform workspace select dev"
echo ""
echo "State backend resources created:"
echo "  S3 Bucket: ${STATE_BUCKET}"
echo "  DynamoDB Table: ${LOCK_TABLE}"
echo "  Region: ${AWS_REGION}"
echo ""
