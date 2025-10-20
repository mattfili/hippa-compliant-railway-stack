# Networking Module - Security Groups

## Overview

This module provisions AWS security groups for a HIPAA-compliant multi-tenant document management system. It implements least-privilege network access controls following a default-deny approach.

## Purpose

Creates three security groups with specific, restricted access rules:

1. **RDS Security Group**: Protects PostgreSQL database access
2. **Application Security Group**: Controls inbound/outbound traffic for backend application
3. **VPC Endpoint Security Group**: Secures private AWS service access

## Security Architecture

### Least-Privilege Design

All security groups follow the principle of least privilege:
- **Default deny**: No unrestricted access (0.0.0.0/0) on sensitive ports
- **Explicit allow**: Only required traffic patterns are permitted
- **Source-specific**: Rules reference other security groups where possible

### Security Group Rules

#### RDS Security Group

**Purpose**: Protects PostgreSQL database with network isolation

**Ingress Rules**:
- Port 5432 (PostgreSQL) from Application Security Group only
- No other inbound traffic allowed

**Egress Rules**:
- None (RDS doesn't require outbound connectivity)
- Implements strict isolation

#### Application Security Group

**Purpose**: Controls traffic for Railway-hosted backend application

**Ingress Rules**:
- Port 443 (HTTPS) from Railway IP ranges (configurable)
- If Railway IP ranges not provided, no ingress rules created

**Egress Rules**:
- Port 5432 (PostgreSQL) to RDS Security Group
- Port 443 (HTTPS) to VPC Endpoint Security Group
- No internet access (uses VPC endpoints for AWS services)

#### VPC Endpoint Security Group

**Purpose**: Secures private AWS service access (S3, Bedrock, RDS)

**Ingress Rules**:
- Port 443 (HTTPS) from Application Security Group only

**Egress Rules**:
- Port 443 (HTTPS) to internet (0.0.0.0/0) for AWS service communication
- Required for VPC interface endpoint functionality

## Dependencies

### Required Modules

- **VPC Module**: Must be deployed first to provide VPC ID

### Required Information

- **Railway IP Ranges**: Obtain from Railway documentation or support
  - If using Railway PrivateLink, IP ranges may not be needed
  - If using public Railway IPs, populate `railway_ip_ranges` variable

## Usage

### Basic Example

```hcl
module "networking" {
  source = "./modules/networking"

  environment = "production"
  vpc_id      = module.vpc.vpc_id

  railway_ip_ranges = [
    "192.0.2.0/24",
    "198.51.100.0/24"
  ]

  tags = {
    Project   = "HIPAA-Compliant-Stack"
    ManagedBy = "Terraform"
  }
}
```

### Development Environment (No Railway IP Restrictions)

```hcl
module "networking" {
  source = "./modules/networking"

  environment        = "dev"
  vpc_id             = module.vpc.vpc_id
  railway_ip_ranges  = []  # Empty for development (no ingress rules created)

  tags = {
    Environment = "dev"
  }
}
```

### Production Environment (Strict IP Allowlist)

```hcl
module "networking" {
  source = "./modules/networking"

  environment = "production"
  vpc_id      = module.vpc.vpc_id

  railway_ip_ranges = [
    "203.0.113.0/24",  # Railway IP range 1
    "198.51.100.0/24"  # Railway IP range 2
  ]

  tags = {
    Environment       = "production"
    ComplianceLevel   = "HIPAA"
    DataClassification = "PHI"
  }
}
```

## Input Variables

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `environment` | `string` | Yes | - | Environment name (dev, staging, production) |
| `vpc_id` | `string` | Yes | - | VPC ID from VPC module (format: vpc-xxxxx) |
| `railway_ip_ranges` | `list(string)` | No | `[]` | Railway IP ranges for HTTPS ingress |
| `tags` | `map(string)` | No | `{}` | Additional tags for resources |

### Variable Validation

- **environment**: Must be one of: `dev`, `staging`, `production`
- **vpc_id**: Must match AWS VPC ID format (`vpc-[a-z0-9]+`)
- **railway_ip_ranges**: All entries must be valid CIDR blocks

## Outputs

| Output | Description |
|--------|-------------|
| `rds_security_group_id` | Security group ID for RDS PostgreSQL |
| `app_security_group_id` | Security group ID for backend application |
| `vpc_endpoint_security_group_id` | Security group ID for VPC endpoints |

### Output Usage in Dependent Modules

```hcl
# RDS Module
module "rds" {
  source = "./modules/rds"

  security_group_id = module.networking.rds_security_group_id
  # ... other variables
}

# VPC Module (for VPC endpoints)
module "vpc" {
  source = "./modules/vpc"

  vpc_endpoint_security_group_id = module.networking.vpc_endpoint_security_group_id
  # ... other variables
}
```

## Railway IP Ranges

### How to Obtain Railway IP Ranges

1. **Railway Documentation**: Check [Railway Docs](https://docs.railway.app) for public IP ranges
2. **Railway Support**: Contact Railway support for current IP allocations
3. **Railway CLI**: Use `railway status` to view deployment network information
4. **Alternative - PrivateLink**: Consider AWS PrivateLink for private connectivity (eliminates need for IP allowlisting)

### Security Considerations

- **IP Range Stability**: Railway IP ranges may change; monitor Railway announcements
- **Backup Access**: Consider alternative access methods (VPN, bastion host) for emergency access
- **Least Privilege**: Only add IP ranges that are actively used by Railway deployments

## HIPAA Compliance

### Technical Safeguards Addressed

- **Access Control (164.312(a)(1))**: Security groups enforce network-level access restrictions
- **Transmission Security (164.312(e))**: HTTPS/TLS enforced for all inbound traffic
- **Network Segmentation**: RDS isolated in private subnets with no direct internet access
- **Audit Controls**: Security group changes logged via CloudTrail

### Compliance Verification

Run these AWS CLI commands to verify security group configuration:

```bash
# Verify RDS has no public access
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=*rds-security-group" \
  --query "SecurityGroups[].IpPermissions"

# Verify no unrestricted ingress (should return no results)
aws ec2 describe-security-groups \
  --filters "Name=ip-permission.cidr,Values=0.0.0.0/0" \
  --query "SecurityGroups[?contains(GroupName, 'rds')]"
```

## Troubleshooting

### Common Issues

#### 1. Application Cannot Connect to RDS

**Symptoms**: Connection timeout or refused errors

**Diagnosis**:
```bash
# Verify security group rules
aws ec2 describe-security-groups --group-ids <rds-sg-id>

# Check security group attachments
aws rds describe-db-instances --query "DBInstances[].VpcSecurityGroups"
```

**Resolution**:
- Ensure application uses app security group
- Verify RDS ingress rule references app security group
- Check VPC subnet routing (application and RDS must be in same VPC)

#### 2. Railway Cannot Reach Application

**Symptoms**: 503 Service Unavailable, connection timeout

**Diagnosis**:
```bash
# Verify app security group has ingress from Railway IPs
aws ec2 describe-security-groups --group-ids <app-sg-id> \
  --query "SecurityGroups[].IpPermissions"
```

**Resolution**:
- Verify `railway_ip_ranges` variable is populated correctly
- Check Railway IP ranges haven't changed
- Consider using Railway PrivateLink for stable connectivity

#### 3. Application Cannot Access S3/Bedrock

**Symptoms**: AWS SDK timeout errors, 403 Forbidden

**Diagnosis**:
```bash
# Verify VPC endpoint security group rules
aws ec2 describe-security-groups --group-ids <vpc-endpoint-sg-id>

# Verify VPC endpoints exist and are associated with security group
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=<vpc-id>"
```

**Resolution**:
- Ensure app security group has egress to VPC endpoint security group (port 443)
- Verify VPC endpoints exist and are using correct security group
- Check VPC endpoint policy allows required actions

### Security Group Rule Limits

AWS limits per security group:
- **Inbound rules**: 60 rules per security group
- **Outbound rules**: 60 rules per security group

If Railway provides many IP ranges, consider:
- Aggregating IP ranges into larger CIDR blocks
- Using multiple security groups
- Implementing AWS PrivateLink for private connectivity

## Maintenance

### Adding New Railway IP Ranges

1. Update `railway_ip_ranges` variable in your terraform.tfvars
2. Run `terraform plan` to review changes
3. Run `terraform apply` to add new ingress rules
4. Verify connectivity from new IP ranges

### Removing Old Railway IP Ranges

1. Remove IP ranges from `railway_ip_ranges` variable
2. Run `terraform plan` to confirm rule removal
3. Run `terraform apply` to remove rules
4. Monitor application logs for connection issues

### Rotating Security Groups

Security groups use `name_prefix` and `create_before_destroy` lifecycle:
- Changes to security group configuration trigger replacement
- New security group created before old one is destroyed
- Minimizes downtime during updates

## Testing

Run module tests:

```bash
cd terraform/tests/unit
go test -v -run TestNetworking -timeout 30m
```

Tests verify:
- All three security groups are created
- Security group IDs are exported
- Tags are applied correctly
- Module works with empty Railway IP ranges

## Version Requirements

- **Terraform**: >= 1.5.0
- **AWS Provider**: >= 5.0

## Authors

Generated with Claude Code for HIPAA-Compliant Railway Stack

## License

See repository LICENSE file
