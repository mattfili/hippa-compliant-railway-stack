#!/bin/bash
set -e

# Terraform Test Runner
# Runs all or specific Terraform tests with proper setup and cleanup

echo "=========================================="
echo "Terraform Infrastructure Test Runner"
echo "=========================================="
echo ""

# Check for required tools
command -v terraform >/dev/null 2>&1 || { echo "ERROR: Terraform not installed. See docs/AWS_TEST_ENVIRONMENT_SETUP.md"; exit 1; }
command -v go >/dev/null 2>&1 || { echo "ERROR: Go not installed. See docs/AWS_TEST_ENVIRONMENT_SETUP.md"; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "ERROR: AWS CLI not installed. See docs/AWS_TEST_ENVIRONMENT_SETUP.md"; exit 1; }

# Check for required environment variables
if [ -z "$AWS_PROFILE" ]; then
    echo "ERROR: AWS_PROFILE not set"
    echo "Run: export AWS_PROFILE=terraform-test"
    exit 1
fi

if [ -z "$AWS_REGION" ]; then
    echo "WARNING: AWS_REGION not set, defaulting to us-east-1"
    export AWS_REGION=us-east-1
fi

# Verify AWS credentials
echo "Verifying AWS credentials..."
aws sts get-caller-identity --profile $AWS_PROFILE > /dev/null || { echo "ERROR: AWS credentials invalid"; exit 1; }
echo "✓ AWS credentials valid"
echo ""

# Navigate to tests directory
cd "$(dirname "$0")/../tests"

# Download Go dependencies
echo "Downloading Go dependencies..."
go mod download
echo "✓ Dependencies ready"
echo ""

# Parse command line arguments
TEST_TYPE=${1:-all}
PARALLEL=${2:-false}

# Function to run a single test
run_test() {
    local test_file=$1
    local test_name=$2
    local timeout=$3

    echo "=========================================="
    echo "Running: $test_name"
    echo "Timeout: $timeout"
    echo "=========================================="
    echo ""

    if [ "$PARALLEL" = "true" ]; then
        go test -v -timeout $timeout -parallel 8 $test_file
    else
        go test -v -timeout $timeout $test_file
    fi

    if [ $? -eq 0 ]; then
        echo ""
        echo "✓ $test_name PASSED"
        echo ""
    else
        echo ""
        echo "✗ $test_name FAILED"
        echo ""
        return 1
    fi
}

# Run tests based on type
case $TEST_TYPE in
    vpc)
        run_test "./unit/vpc_test.go" "VPC Module Test" "30m"
        ;;
    networking)
        run_test "./unit/networking_test.go" "Networking Module Test" "30m"
        ;;
    kms)
        run_test "./unit/kms_test.go" "KMS Module Test" "30m"
        ;;
    s3)
        run_test "./unit/s3_test.go" "S3 Module Test" "30m"
        ;;
    rds)
        echo "⚠️  WARNING: RDS tests take ~20 minutes to run"
        echo "⚠️  WARNING: RDS tests will incur ~$5-8 in AWS costs"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_test "./unit/rds_test.go" "RDS Module Test" "45m"
        else
            echo "RDS tests skipped"
        fi
        ;;
    iam)
        run_test "./unit/iam_test.go" "IAM Module Test" "30m"
        ;;
    config)
        run_test "./unit/config_test.go" "AWS Config Module Test" "30m"
        ;;
    integration)
        echo "⚠️  WARNING: Integration tests deploy full infrastructure"
        echo "⚠️  WARNING: Tests take ~25 minutes and cost ~$8-10"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_test "./integration/full_stack_test.go" "Full Stack Integration Test" "60m"
        else
            echo "Integration tests skipped"
        fi
        ;;
    unit)
        echo "Running all unit tests..."
        run_test "./unit/vpc_test.go" "VPC Module Test" "30m" || true
        run_test "./unit/networking_test.go" "Networking Module Test" "30m" || true
        run_test "./unit/kms_test.go" "KMS Module Test" "30m" || true
        run_test "./unit/s3_test.go" "S3 Module Test" "30m" || true
        run_test "./unit/iam_test.go" "IAM Module Test" "30m" || true
        run_test "./unit/config_test.go" "AWS Config Module Test" "30m" || true

        echo ""
        echo "⚠️  RDS test skipped (requires explicit confirmation)"
        echo "Run: ./scripts/run-tests.sh rds"
        ;;
    all)
        echo "⚠️  WARNING: Running all tests will take ~60 minutes"
        echo "⚠️  WARNING: Total AWS cost: ~$10-15"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            go test -v -timeout 90m ./...
        else
            echo "Tests cancelled. Run specific tests with: ./scripts/run-tests.sh [vpc|networking|kms|s3|rds|iam|config|integration|unit]"
        fi
        ;;
    *)
        echo "Usage: ./scripts/run-tests.sh [TEST_TYPE] [PARALLEL]"
        echo ""
        echo "TEST_TYPE options:"
        echo "  vpc          - Run VPC module tests (~5 min, ~$0.50)"
        echo "  networking   - Run Networking module tests (~3 min, ~$0.30)"
        echo "  kms          - Run KMS module tests (~2 min, ~$0.10)"
        echo "  s3           - Run S3 module tests (~3 min, ~$0.20)"
        echo "  rds          - Run RDS module tests (~20 min, ~$5-8)"
        echo "  iam          - Run IAM module tests (~2 min, ~$0.10)"
        echo "  config       - Run AWS Config module tests (~3 min, ~$0.30)"
        echo "  integration  - Run full stack integration tests (~25 min, ~$8-10)"
        echo "  unit         - Run all unit tests except RDS (~20 min, ~$2)"
        echo "  all          - Run ALL tests (~60 min, ~$10-15)"
        echo ""
        echo "PARALLEL options:"
        echo "  true         - Run tests in parallel (faster, more AWS resources)"
        echo "  false        - Run tests sequentially (default, safer)"
        echo ""
        echo "Examples:"
        echo "  ./scripts/run-tests.sh vpc           # Run VPC tests"
        echo "  ./scripts/run-tests.sh unit          # Run all unit tests except RDS"
        echo "  ./scripts/run-tests.sh all true      # Run all tests in parallel"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✓ Test run complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  - Review test output above"
echo "  - Check AWS Console to verify resource cleanup"
echo "  - Run: aws ec2 describe-vpcs --profile $AWS_PROFILE --region $AWS_REGION"
echo ""
