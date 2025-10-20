#!/bin/bash

# ==============================================================================
# AWS Infrastructure Cost Estimation Script
# ==============================================================================
# Estimates monthly AWS costs for the HIPAA-compliant infrastructure stack
# based on Terraform plan output
# ==============================================================================

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==============================================================================
# Cost Constants (USD per month, us-east-1 region)
# ==============================================================================

# RDS Pricing (On-Demand, Monthly)
declare -A RDS_PRICING
RDS_PRICING["db.t3.micro"]=14
RDS_PRICING["db.t3.small"]=28
RDS_PRICING["db.t3.medium"]=56
RDS_PRICING["db.t3.large"]=112
RDS_PRICING["db.r6g.xlarge"]=266

# Storage Pricing (gp3)
RDS_STORAGE_GB_MONTH=0.12
RDS_BACKUP_STORAGE_GB_MONTH=0.095

# S3 Pricing
S3_STANDARD_GB_MONTH=0.023
S3_STANDARD_IA_GB_MONTH=0.0125
S3_GLACIER_GB_MONTH=0.004

# NAT Gateway Pricing
NAT_GATEWAY_HOUR=0.045
NAT_GATEWAY_DATA_GB=0.045
HOURS_PER_MONTH=730

# VPC Endpoint Pricing
VPC_ENDPOINT_HOUR=0.01
VPC_ENDPOINT_DATA_GB=0.01

# ==============================================================================
# Functions
# ==============================================================================

print_header() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${YELLOW}--- $1 ---${NC}"
}

print_cost() {
    local service=$1
    local cost=$2
    printf "  %-30s \$%.2f/month\n" "$service" "$cost"
}

estimate_rds_cost() {
    local instance_class=$1
    local storage_gb=$2
    local multi_az=$3
    local read_replica=$4
    local backup_storage_gb=${5:-50}

    local instance_cost=${RDS_PRICING[$instance_class]:-60}
    local storage_cost=$(echo "$storage_gb * $RDS_STORAGE_GB_MONTH" | bc)
    local backup_cost=$(echo "$backup_storage_gb * $RDS_BACKUP_STORAGE_GB_MONTH" | bc)

    local total=$instance_cost

    # Multi-AZ doubles the instance cost
    if [[ "$multi_az" == "true" ]]; then
        total=$(echo "$total * 2" | bc)
    fi

    # Read replica adds another instance
    if [[ "$read_replica" == "true" ]]; then
        total=$(echo "$total + $instance_cost" | bc)
    fi

    # Add storage and backup costs
    total=$(echo "$total + $storage_cost + $backup_cost" | bc)

    echo "$total"
}

estimate_s3_cost() {
    local data_gb=${1:-100}

    # Assume 50% in Standard, 30% in Standard-IA, 20% in Glacier (with lifecycle)
    local standard_cost=$(echo "$data_gb * 0.5 * $S3_STANDARD_GB_MONTH" | bc)
    local ia_cost=$(echo "$data_gb * 0.3 * $S3_STANDARD_IA_GB_MONTH" | bc)
    local glacier_cost=$(echo "$data_gb * 0.2 * $S3_GLACIER_GB_MONTH" | bc)

    local total=$(echo "$standard_cost + $ia_cost + $glacier_cost" | bc)
    echo "$total"
}

estimate_nat_gateway_cost() {
    local num_gateways=$1
    local data_processed_gb=${2:-1000}

    local hourly_cost=$(echo "$num_gateways * $NAT_GATEWAY_HOUR * $HOURS_PER_MONTH" | bc)
    local data_cost=$(echo "$data_processed_gb * $NAT_GATEWAY_DATA_GB" | bc)

    local total=$(echo "$hourly_cost + $data_cost" | bc)
    echo "$total"
}

estimate_vpc_endpoint_cost() {
    local num_endpoints=$1
    local data_processed_gb=${2:-1000}

    # Interface endpoints cost per hour
    local hourly_cost=$(echo "$num_endpoints * $VPC_ENDPOINT_HOUR * $HOURS_PER_MONTH" | bc)
    local data_cost=$(echo "$data_processed_gb * $VPC_ENDPOINT_DATA_GB" | bc)

    local total=$(echo "$hourly_cost + $data_cost" | bc)
    echo "$total"
}

# ==============================================================================
# Environment Cost Estimations
# ==============================================================================

estimate_dev_environment() {
    print_section "Development Environment"

    local rds_cost=$(estimate_rds_cost "db.t3.medium" 20 false false 20)
    local s3_cost=$(estimate_s3_cost 50)
    local nat_cost=0  # Typically disabled in dev
    local vpc_endpoint_cost=$(estimate_vpc_endpoint_cost 2 100)
    local cloudwatch_cost=10  # Minimal logging
    local config_cost=5  # Minimal Config usage

    print_cost "RDS PostgreSQL" "$rds_cost"
    print_cost "S3 Storage" "$s3_cost"
    print_cost "VPC Endpoints" "$vpc_endpoint_cost"
    print_cost "CloudWatch Logs" "$cloudwatch_cost"
    print_cost "AWS Config" "$config_cost"

    local total=$(echo "$rds_cost + $s3_cost + $vpc_endpoint_cost + $cloudwatch_cost + $config_cost" | bc)
    echo ""
    echo -e "  ${GREEN}Total Estimated Cost: \$$(printf '%.2f' $total)/month${NC}"
}

estimate_staging_environment() {
    print_section "Staging Environment"

    local rds_cost=$(estimate_rds_cost "db.t3.large" 50 true false 50)
    local s3_cost=$(estimate_s3_cost 200)
    local nat_cost=$(estimate_nat_gateway_cost 3 500)
    local vpc_endpoint_cost=$(estimate_vpc_endpoint_cost 3 500)
    local cloudwatch_cost=30  # Moderate logging
    local config_cost=15  # Full Config monitoring

    print_cost "RDS PostgreSQL (Multi-AZ)" "$rds_cost"
    print_cost "S3 Storage" "$s3_cost"
    print_cost "NAT Gateways (3 AZs)" "$nat_cost"
    print_cost "VPC Endpoints" "$vpc_endpoint_cost"
    print_cost "CloudWatch Logs" "$cloudwatch_cost"
    print_cost "AWS Config" "$config_cost"

    local total=$(echo "$rds_cost + $s3_cost + $nat_cost + $vpc_endpoint_cost + $cloudwatch_cost + $config_cost" | bc)
    echo ""
    echo -e "  ${GREEN}Total Estimated Cost: \$$(printf '%.2f' $total)/month${NC}"
}

estimate_production_environment() {
    print_section "Production Environment"

    local rds_cost=$(estimate_rds_cost "db.r6g.xlarge" 100 true true 200)
    local s3_cost=$(estimate_s3_cost 1000)
    local nat_cost=$(estimate_nat_gateway_cost 3 2000)
    local vpc_endpoint_cost=$(estimate_vpc_endpoint_cost 3 2000)
    local cloudwatch_cost=100  # Extensive logging
    local config_cost=30  # Full Config monitoring
    local cloudtrail_cost=10  # CloudTrail logging

    print_cost "RDS PostgreSQL (Multi-AZ + Replica)" "$rds_cost"
    print_cost "S3 Storage (1TB)" "$s3_cost"
    print_cost "NAT Gateways (3 AZs)" "$nat_cost"
    print_cost "VPC Endpoints" "$vpc_endpoint_cost"
    print_cost "CloudWatch Logs" "$cloudwatch_cost"
    print_cost "AWS Config" "$config_cost"
    print_cost "CloudTrail" "$cloudtrail_cost"

    local total=$(echo "$rds_cost + $s3_cost + $nat_cost + $vpc_endpoint_cost + $cloudwatch_cost + $config_cost + $cloudtrail_cost" | bc)
    echo ""
    echo -e "  ${GREEN}Total Estimated Cost: \$$(printf '%.2f' $total)/month${NC}"

    # Show savings with Reserved Instances
    echo ""
    echo -e "  ${YELLOW}Note: With RDS Reserved Instances (1-year), save up to 40%${NC}"
    local ri_savings=$(echo "$total * 0.4" | bc)
    local total_with_ri=$(echo "$total - $ri_savings" | bc)
    echo -e "  ${GREEN}Estimated with RI: \$$(printf '%.2f' $total_with_ri)/month${NC}"
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    print_header "AWS Infrastructure Cost Estimation"

    echo "This script provides estimated monthly costs for the HIPAA-compliant"
    echo "infrastructure stack across development, staging, and production environments."
    echo ""
    echo "Costs are based on:"
    echo "  - AWS us-east-1 region pricing (October 2025)"
    echo "  - On-Demand pricing (without Reserved Instances or Savings Plans)"
    echo "  - Estimated data transfer and storage usage"
    echo ""
    echo -e "${RED}Note: These are estimates only. Actual costs may vary based on usage.${NC}"

    estimate_dev_environment
    estimate_staging_environment
    estimate_production_environment

    print_header "Cost Optimization Tips"

    echo "1. Use Reserved Instances for production RDS (save 40-60%)"
    echo "2. Enable S3 lifecycle policies to transition to cheaper storage tiers"
    echo "3. Use VPC endpoints instead of NAT Gateways to reduce data transfer costs"
    echo "4. Right-size RDS instances based on actual usage metrics"
    echo "5. Enable CloudWatch detailed monitoring only when needed"
    echo "6. Set appropriate log retention periods (default: 90 days)"
    echo "7. Use Savings Plans for predictable workloads"
    echo ""

    print_header "Additional Resources"

    echo "For detailed pricing information:"
    echo "  - RDS: https://aws.amazon.com/rds/postgresql/pricing/"
    echo "  - S3: https://aws.amazon.com/s3/pricing/"
    echo "  - VPC: https://aws.amazon.com/vpc/pricing/"
    echo "  - AWS Calculator: https://calculator.aws/"
    echo ""
}

# Run main function
main
