#!/bin/bash
set -e

# Fix backend.tf by replacing placeholder with actual AWS account ID

echo "=========================================="
echo "Fixing backend.tf Configuration"
echo "=========================================="
echo ""

# Check for AWS credentials
if [ -z "$AWS_PROFILE" ]; then
    echo "ERROR: AWS_PROFILE not set"
    echo "Run: export AWS_PROFILE=terraform-test"
    exit 1
fi

# Get AWS account ID
echo "Getting AWS account ID..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile $AWS_PROFILE 2>/dev/null)

if [ -z "$ACCOUNT_ID" ]; then
    echo "ERROR: Could not retrieve AWS account ID"
    echo "Check your AWS credentials: aws sts get-caller-identity --profile $AWS_PROFILE"
    exit 1
fi

echo "✓ AWS Account ID: $ACCOUNT_ID"
echo ""

# Navigate to terraform directory
cd "$(dirname "$0")/.."

# Backup original backend.tf
if [ ! -f backend.tf.original ]; then
    cp backend.tf backend.tf.original
    echo "✓ Created backup: backend.tf.original"
fi

# Fix the backend.tf file - replace the invalid variable syntax
echo "Updating backend.tf..."

# Replace terraform-state-hipaa-${aws_account_id} with actual value
sed -i.tmp "s/terraform-state-hipaa-\${aws_account_id}/terraform-state-dev-${ACCOUNT_ID}/g" backend.tf
rm -f backend.tf.tmp

# Also handle the placeholder pattern from comments
sed -i.tmp "s/terraform-state-hipaa-123456789012/terraform-state-dev-${ACCOUNT_ID}/g" backend.tf
rm -f backend.tf.tmp

echo "✓ Updated backend.tf with account ID: $ACCOUNT_ID"
echo ""

# Show the updated backend configuration
echo "Updated backend configuration:"
echo "----------------------------------------"
grep -A 2 "bucket =" backend.tf
echo "----------------------------------------"
echo ""

echo "✓ backend.tf fixed!"
echo ""
echo "Next steps:"
echo "1. Run: terraform init"
echo "2. Run: terraform workspace new dev"
echo "3. Run: terraform workspace select dev"
echo ""
