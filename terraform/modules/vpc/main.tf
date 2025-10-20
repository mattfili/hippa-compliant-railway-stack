# ==============================================================================
# VPC Module - Main Configuration
# ==============================================================================
# This module provisions VPC, subnets, routing, NAT gateways, Internet Gateway,
# and VPC endpoints for secure, multi-AZ AWS infrastructure
# ==============================================================================

locals {
  # Construct environment label with optional suffix for test isolation
  env_label   = var.environment
  full_suffix = var.name_suffix == "" ? local.env_label : "${local.env_label}-${var.name_suffix}"

  # Calculate subnet CIDRs dynamically
  public_subnet_cidrs  = [for i in range(3) : cidrsubnet(var.vpc_cidr, 8, i)]
  private_subnet_cidrs = [for i in range(3) : cidrsubnet(var.vpc_cidr, 8, i + 10)]

  # Common tags for all resources
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      Context     = var.name_suffix
      ManagedBy   = "Terraform"
      Module      = "vpc"
    }
  )
}

# ==============================================================================
# VPC Resource
# ==============================================================================

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-compliant-vpc-${local.full_suffix}"
    }
  )
}

# ==============================================================================
# Public Subnets (for NAT Gateways, Load Balancers)
# ==============================================================================

resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-public-subnet-${var.environment}-${count.index + 1}"
      Tier = "Public"
      AZ   = var.availability_zones[count.index]
    }
  )
}

# ==============================================================================
# Private Subnets (for RDS, Application Endpoints)
# ==============================================================================

resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-private-subnet-${var.environment}-${count.index + 1}"
      Tier = "Private"
      AZ   = var.availability_zones[count.index]
    }
  )
}

# ==============================================================================
# Internet Gateway (for public subnet internet access)
# ==============================================================================

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-igw-${var.environment}"
    }
  )
}

# ==============================================================================
# Elastic IPs for NAT Gateways
# ==============================================================================

resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 3 : 0
  domain = "vpc"

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-nat-eip-${var.environment}-${count.index + 1}"
    }
  )

  depends_on = [aws_internet_gateway.main]
}

# ==============================================================================
# NAT Gateways (one per AZ for high availability)
# ==============================================================================

resource "aws_nat_gateway" "main" {
  count         = var.enable_nat_gateway ? 3 : 0
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-nat-gw-${var.environment}-${count.index + 1}"
      AZ   = var.availability_zones[count.index]
    }
  )

  depends_on = [aws_internet_gateway.main]
}

# ==============================================================================
# Route Tables - Public
# ==============================================================================

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-public-rt-${var.environment}"
      Tier = "Public"
    }
  )
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  count          = 3
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ==============================================================================
# Route Tables - Private (one per AZ)
# ==============================================================================

resource "aws_route_table" "private" {
  count  = 3
  vpc_id = aws_vpc.main.id

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-private-rt-${var.environment}-${count.index + 1}"
      Tier = "Private"
      AZ   = var.availability_zones[count.index]
    }
  )
}

resource "aws_route" "private_nat" {
  count                  = var.enable_nat_gateway ? 3 : 0
  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main[count.index].id
}

resource "aws_route_table_association" "private" {
  count          = 3
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ==============================================================================
# VPC Endpoints - Gateway Endpoint for S3
# ==============================================================================

resource "aws_vpc_endpoint" "s3" {
  count        = var.enable_vpc_endpoints ? 1 : 0
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${data.aws_region.current.name}.s3"

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-s3-endpoint-${var.environment}"
    }
  )
}

resource "aws_vpc_endpoint_route_table_association" "s3_private" {
  count           = var.enable_vpc_endpoints ? 3 : 0
  route_table_id  = aws_route_table.private[count.index].id
  vpc_endpoint_id = aws_vpc_endpoint.s3[0].id
}

# ==============================================================================
# VPC Endpoints - Interface Endpoints
# ==============================================================================

# Security group for interface endpoints
resource "aws_security_group" "vpc_endpoints" {
  count       = var.enable_vpc_endpoints ? 1 : 0
  name        = "hipaa-vpc-endpoints-sg-${var.environment}"
  description = "Security group for VPC interface endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-vpc-endpoints-sg-${var.environment}"
    }
  )
}

# RDS Interface Endpoint
resource "aws_vpc_endpoint" "rds" {
  count               = var.enable_vpc_endpoints ? 1 : 0
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.rds"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-rds-endpoint-${var.environment}"
    }
  )
}

# Bedrock Runtime Interface Endpoint
resource "aws_vpc_endpoint" "bedrock" {
  count               = var.enable_vpc_endpoints ? 1 : 0
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true

  tags = merge(
    local.common_tags,
    {
      Name = "hipaa-bedrock-endpoint-${var.environment}"
    }
  )
}

# ==============================================================================
# Data Sources
# ==============================================================================

data "aws_region" "current" {}
