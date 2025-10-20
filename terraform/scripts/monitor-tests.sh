#!/bin/bash

# Monitor Test Progress
# Shows real-time status of running Terraform tests

echo "=========================================="
echo "Terraform Test Monitor"
echo "=========================================="
echo ""

# Check for test log files
cd /Users/mattfili/Dev/hippa-compliant-railway-stack/terraform/tests

echo "Checking for running tests..."
echo ""

# Look for test processes
if pgrep -f "go test.*vpc_test.go" > /dev/null; then
    echo "✓ VPC tests RUNNING"
else
    echo "✗ VPC tests not running"
fi

if pgrep -f "go test.*networking_test.go" > /dev/null; then
    echo "✓ Networking tests RUNNING"
else
    echo "✗ Networking tests not running"
fi

if pgrep -f "go test.*kms_test.go" > /dev/null; then
    echo "✓ KMS tests RUNNING"
else
    echo "✗ KMS tests not running"
fi

if pgrep -f "go test.*s3_test.go" > /dev/null; then
    echo "✓ S3 tests RUNNING"
else
    echo "✗ S3 tests not running"
fi

if pgrep -f "go test.*iam_test.go" > /dev/null; then
    echo "✓ IAM tests RUNNING"
else
    echo "✗ IAM tests not running"
fi

if pgrep -f "go test.*config_test.go" > /dev/null; then
    echo "✓ Config tests RUNNING"
else
    echo "✗ Config tests not running"
fi

if pgrep -f "go test.*rds_test.go" > /dev/null; then
    echo "✓ RDS tests RUNNING"
else
    echo "✗ RDS tests not running"
fi

echo ""
echo "To view test output in real-time:"
echo "  tail -f /tmp/vpc_test.log"
echo "  tail -f /tmp/s3_test.log"
echo ""
echo "To kill all tests:"
echo "  pkill -f 'go test'"
echo ""
