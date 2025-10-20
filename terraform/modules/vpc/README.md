# VPC Module

## Purpose

Provision VPC with multi-AZ architecture, subnets, routing, NAT gateways, Internet Gateway, and VPC endpoints for secure, private AWS service access. This module establishes the foundational networking infrastructure for HIPAA-compliant applications.

## Features

- **Multi-AZ Architecture**: Deploys resources across 3 availability zones for high availability
- **Public & Private Subnets**: 3 public subnets for NAT Gateways and 3 private subnets for RDS/application resources
- **Internet Gateway**: Provides internet access for public subnets
- **NAT Gateways**: One per AZ for high-availability private subnet internet access
- **VPC Endpoints**: Gateway endpoint for S3 and interface endpoints for RDS and Bedrock (cost-optimized, private connectivity)
- **DNS Support**: Enables DNS resolution and hostnames within VPC

## Usage

### Basic Example

```hcl
module "vpc" {
  source = "./modules/vpc"

  environment        = "production"
  vpc_cidr           = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

  tags = {
    Project = "HIPAA Compliant Stack"
    Owner   = "Platform Team"
  }
}
```

### Cost-Optimized Development Environment

```hcl
module "vpc" {
  source = "./modules/vpc"

  environment         = "dev"
  vpc_cidr            = "10.0.0.0/16"
  enable_nat_gateway  = false  # Disable NAT gateways to save costs in dev
  enable_vpc_endpoints = false  # Disable VPC endpoints in dev

  tags = {
    Environment = "Development"
    CostCenter  = "Engineering"
  }
}
```

### Production with Full Features

```hcl
module "vpc" {
  source = "./modules/vpc"

  environment         = "production"
  vpc_cidr            = "10.0.0.0/16"
  availability_zones  = ["us-east-1a", "us-east-1b", "us-east-1c"]
  enable_nat_gateway  = true
  enable_vpc_endpoints = true

  tags = {
    Environment = "Production"
    Compliance  = "HIPAA"
    Project     = "Document Management"
  }
}
```

## Input Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `vpc_cidr` | string | `"10.0.0.0/16"` | CIDR block for VPC |
| `environment` | string | *required* | Environment name (dev, staging, production) |
| `availability_zones` | list(string) | `["us-east-1a", "us-east-1b", "us-east-1c"]` | Availability zones for multi-AZ deployment |
| `enable_nat_gateway` | bool | `true` | Enable NAT gateway for private subnet internet access |
| `enable_vpc_endpoints` | bool | `true` | Enable VPC endpoints for S3, RDS, Bedrock |
| `tags` | map(string) | `{}` | Additional resource tags |

## Output Values

| Output | Description |
|--------|-------------|
| `vpc_id` | VPC ID |
| `vpc_cidr_block` | VPC CIDR block |
| `private_subnet_ids` | List of private subnet IDs (for RDS, app endpoints) |
| `public_subnet_ids` | List of public subnet IDs (for NAT gateways) |
| `vpc_endpoint_s3_id` | S3 VPC endpoint ID (empty if disabled) |
| `vpc_endpoint_rds_id` | RDS VPC endpoint ID (empty if disabled) |
| `vpc_endpoint_bedrock_id` | Bedrock VPC endpoint ID (empty if disabled) |
| `nat_gateway_ids` | List of NAT Gateway IDs |
| `internet_gateway_id` | Internet Gateway ID |
| `private_route_table_ids` | List of private route table IDs |
| `public_route_table_id` | Public route table ID |

## Architecture

### Network Layout

- **Public Subnets** (3):
  - CIDR: 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24
  - Purpose: NAT Gateways, Load Balancers
  - Internet access: Via Internet Gateway

- **Private Subnets** (3):
  - CIDR: 10.0.11.0/24, 10.0.12.0/24, 10.0.13.0/24
  - Purpose: RDS, Application endpoints
  - Internet access: Via NAT Gateways (if enabled)

### VPC Endpoints

- **S3 Gateway Endpoint** (Free): Private access to S3 without NAT Gateway data transfer charges
- **RDS Interface Endpoint**: Private access to RDS API
- **Bedrock Interface Endpoint**: Private access to Bedrock Runtime API

## Dependencies

None - This is a foundational module with no dependencies on other modules.

## Security Considerations

- **No Public RDS**: Private subnets ensure RDS instances have no public IPs
- **Least Privilege**: Security groups on VPC endpoints restrict access to VPC CIDR only
- **Defense in Depth**: Multiple layers of network isolation (subnets, route tables, security groups)
- **Cost vs Security**: NAT Gateways can be disabled in dev environments but should be enabled in production

## Cost Optimization

### Development Environment
- Disable NAT Gateways (`enable_nat_gateway = false`): Save ~$100/month
- Disable VPC Endpoints (`enable_vpc_endpoints = false`): Save ~$15/month
- **Total Savings**: ~$115/month for dev

### Production Environment
- Keep NAT Gateways enabled for high availability
- Use S3 Gateway Endpoint (free) to avoid NAT data transfer charges (~$45/GB)
- Interface endpoints cost ~$7/month each but save on NAT data transfer

## Terraform Commands

```bash
# Initialize module
terraform init

# Validate configuration
terraform validate

# Format code
terraform fmt

# Plan deployment
terraform plan

# Apply configuration
terraform apply

# Destroy resources
terraform destroy
```

## Testing

Tests for this module are located in `/terraform/tests/unit/vpc_test.go`. Run tests with:

```bash
cd terraform/tests
go test -v ./unit/vpc_test.go
```

## Troubleshooting

### Common Issues

**Error: "VPC endpoint already exists"**
- Check if VPC endpoints were created manually
- Solution: Import existing endpoint or delete and recreate

**Error: "NAT Gateway creation failed"**
- Ensure Elastic IPs are allocated successfully
- Verify Internet Gateway is created first
- Solution: Check AWS service limits for EIPs

**Slow apply/destroy**
- NAT Gateways take 5-10 minutes to create/destroy
- Expected behavior - be patient

## Version History

- **v1.0.0** (2025-10-17): Initial implementation with multi-AZ support, VPC endpoints

## Authors

- Platform Team - Initial implementation via Terraform module development
