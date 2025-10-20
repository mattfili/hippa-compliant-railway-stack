#!/bin/bash
# ==============================================================================
# Railway Integration Test Script
# ==============================================================================
# This script validates the Railway integration components without actually
# deploying to Railway. It performs the following checks:
# 1. Validates railway.json syntax
# 2. Checks Terraform Dockerfile exists and has required components
# 3. Validates load-terraform-outputs.sh script
# 4. Tests mock Terraform outputs processing
# 5. Validates startup.sh integration
# 6. Checks config.py has required fields
# ==============================================================================

set -e

echo "=========================================="
echo "Railway Integration Validation"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ERRORS=$((ERRORS + 1))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# ------------------------------------------------------------------------------
# Test 1: Validate railway.json
# ------------------------------------------------------------------------------
echo "[Test 1/7] Validating railway.json..."

if [ -f "backend/railway.json" ]; then
    if python3 -m json.tool backend/railway.json > /dev/null 2>&1; then
        pass "railway.json is valid JSON"

        # Check for required services
        if grep -q '"name": "terraform"' backend/railway.json; then
            pass "Terraform service defined"
        else
            fail "Terraform service not found in railway.json"
        fi

        if grep -q '"name": "backend"' backend/railway.json; then
            pass "Backend service defined"
        else
            fail "Backend service not found in railway.json"
        fi

        if grep -q '"dependsOn": \["terraform"\]' backend/railway.json; then
            pass "Backend service depends on Terraform"
        else
            fail "Backend service dependency on Terraform not found"
        fi
    else
        fail "railway.json is invalid JSON"
    fi
else
    fail "railway.json not found at backend/railway.json"
fi

echo ""

# ------------------------------------------------------------------------------
# Test 2: Validate Terraform Dockerfile
# ------------------------------------------------------------------------------
echo "[Test 2/7] Validating Terraform Dockerfile..."

if [ -f "terraform/Dockerfile" ]; then
    pass "Terraform Dockerfile exists"

    if grep -q "FROM hashicorp/terraform" terraform/Dockerfile; then
        pass "Dockerfile uses Terraform base image"
    else
        fail "Dockerfile does not use Terraform base image"
    fi

    if grep -q "jq" terraform/Dockerfile; then
        pass "Dockerfile installs jq for JSON parsing"
    else
        fail "Dockerfile does not install jq"
    fi
else
    fail "Terraform Dockerfile not found at terraform/Dockerfile"
fi

echo ""

# ------------------------------------------------------------------------------
# Test 3: Validate load-terraform-outputs.sh
# ------------------------------------------------------------------------------
echo "[Test 3/7] Validating load-terraform-outputs.sh..."

if [ -f "backend/scripts/load-terraform-outputs.sh" ]; then
    pass "load-terraform-outputs.sh exists"

    if [ -x "backend/scripts/load-terraform-outputs.sh" ]; then
        pass "load-terraform-outputs.sh is executable"
    else
        fail "load-terraform-outputs.sh is not executable"
    fi

    # Check for required exports
    required_exports=(
        "RDS_ENDPOINT"
        "RDS_DB_NAME"
        "RDS_USERNAME"
        "S3_BUCKET_DOCUMENTS"
        "S3_BUCKET_BACKUPS"
        "S3_BUCKET_AUDIT_LOGS"
        "KMS_MASTER_KEY_ID"
        "DATABASE_URL"
    )

    for export_var in "${required_exports[@]}"; do
        if grep -q "export $export_var" backend/scripts/load-terraform-outputs.sh; then
            pass "Exports $export_var"
        else
            fail "Does not export $export_var"
        fi
    done
else
    fail "load-terraform-outputs.sh not found"
fi

echo ""

# ------------------------------------------------------------------------------
# Test 4: Test mock Terraform outputs processing
# ------------------------------------------------------------------------------
echo "[Test 4/7] Testing Terraform outputs processing..."

# Create mock outputs.json
MOCK_OUTPUTS_DIR="/tmp/railway-test-$$"
mkdir -p "$MOCK_OUTPUTS_DIR"

cat > "$MOCK_OUTPUTS_DIR/outputs.json" << 'EOF'
{
  "rds_endpoint": {"value": "db-test.xxx.us-east-1.rds.amazonaws.com:5432"},
  "rds_reader_endpoint": {"value": "db-test-ro.xxx.us-east-1.rds.amazonaws.com:5432"},
  "rds_db_name": {"value": "hipaa_test_db"},
  "rds_username": {"value": "test_user"},
  "s3_bucket_documents": {"value": "hipaa-docs-test-123456"},
  "s3_bucket_backups": {"value": "hipaa-backups-test-123456"},
  "s3_bucket_audit_logs": {"value": "hipaa-audit-test-123456"},
  "kms_master_key_id": {"value": "arn:aws:kms:us-east-1:123456:key/test-key"},
  "kms_master_key_arn": {"value": "arn:aws:kms:us-east-1:123456:key/test-key"},
  "vpc_id": {"value": "vpc-test123"},
  "app_iam_role_arn": {"value": "arn:aws:iam::123456:role/test-role"},
  "aws_region": {"value": "us-east-1"}
}
EOF

# Test jq parsing
if command -v jq &> /dev/null; then
    pass "jq is installed"

    # Test parsing each field
    RDS_ENDPOINT=$(jq -r '.rds_endpoint.value' "$MOCK_OUTPUTS_DIR/outputs.json")
    if [ "$RDS_ENDPOINT" = "db-test.xxx.us-east-1.rds.amazonaws.com:5432" ]; then
        pass "Successfully parsed RDS_ENDPOINT"
    else
        fail "Failed to parse RDS_ENDPOINT (got: $RDS_ENDPOINT)"
    fi
else
    warn "jq not installed - skipping JSON parsing test"
fi

# Cleanup
rm -rf "$MOCK_OUTPUTS_DIR"

echo ""

# ------------------------------------------------------------------------------
# Test 5: Validate startup.sh integration
# ------------------------------------------------------------------------------
echo "[Test 5/7] Validating startup.sh integration..."

if [ -f "backend/scripts/startup.sh" ]; then
    pass "startup.sh exists"

    if [ -x "backend/scripts/startup.sh" ]; then
        pass "startup.sh is executable"
    else
        fail "startup.sh is not executable"
    fi

    if grep -q "load-terraform-outputs.sh" backend/scripts/startup.sh; then
        pass "startup.sh sources load-terraform-outputs.sh"
    else
        fail "startup.sh does not source load-terraform-outputs.sh"
    fi

    if grep -q "/terraform/outputs.json" backend/scripts/startup.sh; then
        pass "startup.sh checks for Terraform outputs file"
    else
        fail "startup.sh does not check for Terraform outputs file"
    fi
else
    fail "startup.sh not found"
fi

echo ""

# ------------------------------------------------------------------------------
# Test 6: Validate config.py fields
# ------------------------------------------------------------------------------
echo "[Test 6/7] Validating config.py AWS infrastructure fields..."

if [ -f "backend/app/config.py" ]; then
    pass "config.py exists"

    # Check for new AWS infrastructure fields
    aws_fields=(
        "s3_bucket_documents"
        "s3_bucket_backups"
        "s3_bucket_audit_logs"
        "kms_master_key_id"
    )

    for field in "${aws_fields[@]}"; do
        if grep -q "$field:" backend/app/config.py; then
            pass "Config has $field field"
        else
            fail "Config missing $field field"
        fi
    done
else
    fail "config.py not found"
fi

echo ""

# ------------------------------------------------------------------------------
# Test 7: Validate documentation
# ------------------------------------------------------------------------------
echo "[Test 7/7] Validating documentation..."

if [ -f "docs/RAILWAY_ENVIRONMENT_VARIABLES.md" ]; then
    pass "Environment variables documentation exists"

    # Check documentation completeness
    if grep -q "User-Provided Environment Variables" docs/RAILWAY_ENVIRONMENT_VARIABLES.md; then
        pass "Documentation includes user-provided variables section"
    else
        fail "Documentation missing user-provided variables section"
    fi

    if grep -q "Auto-Generated Environment Variables" docs/RAILWAY_ENVIRONMENT_VARIABLES.md; then
        pass "Documentation includes auto-generated variables section"
    else
        fail "Documentation missing auto-generated variables section"
    fi

    if grep -q "Troubleshooting" docs/RAILWAY_ENVIRONMENT_VARIABLES.md; then
        pass "Documentation includes troubleshooting section"
    else
        fail "Documentation missing troubleshooting section"
    fi
else
    fail "Environment variables documentation not found"
fi

echo ""

# ------------------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------------------
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    echo "Railway integration is properly configured."
    echo ""
    echo "Next steps:"
    echo "1. Ensure Terraform modules are implemented (Groups 1-9)"
    echo "2. Configure Railway environment variables"
    echo "3. Push to GitHub to trigger Railway deployment"
    echo "4. Monitor Terraform service logs"
    echo "5. Verify backend service starts successfully"
else
    echo -e "${RED}$ERRORS test(s) failed${NC}"
    echo "Please fix the issues above before deploying to Railway."
    exit 1
fi
echo "=========================================="
