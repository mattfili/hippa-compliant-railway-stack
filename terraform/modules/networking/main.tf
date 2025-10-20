# ==============================================================================
# Security Groups Module - Main Configuration
# ==============================================================================
# Implements least-privilege security groups for RDS, application, and VPC endpoints
# Following HIPAA technical safeguards with default-deny approach
# ==============================================================================

locals {
  # Construct environment label with optional suffix for test isolation
  env_label   = var.environment
  full_suffix = var.name_suffix == "" ? local.env_label : "${local.env_label}-${var.name_suffix}"

  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      Context     = var.name_suffix
      ManagedBy   = "Terraform"
    }
  )
}

# ------------------------------------------------------------------------------
# RDS Security Group
# ------------------------------------------------------------------------------
# Allows PostgreSQL (port 5432) access only from application security group
# No egress rules (RDS doesn't need outbound connectivity)
# ------------------------------------------------------------------------------

resource "aws_security_group" "rds" {
  name_prefix = "${local.full_suffix}-rds-sg-"
  description = "Security group for RDS PostgreSQL database - allows access only from application"
  vpc_id      = var.vpc_id

  tags = merge(
    local.common_tags,
    {
      Name    = "${local.full_suffix}-rds-security-group"
      Purpose = "RDS-PostgreSQL"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# Ingress rule: Allow PostgreSQL from application security group
resource "aws_security_group_rule" "rds_ingress_from_app" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.app.id
  security_group_id        = aws_security_group.rds.id
  description              = "Allow PostgreSQL access from application security group"
}

# No egress rules for RDS - implements least-privilege principle
# RDS instances don't require outbound connectivity

# ------------------------------------------------------------------------------
# Application Security Group
# ------------------------------------------------------------------------------
# Ingress: HTTPS (443) from Railway IP ranges
# Egress: PostgreSQL (5432) to RDS, HTTPS (443) to VPC endpoints
# ------------------------------------------------------------------------------

resource "aws_security_group" "app" {
  name_prefix = "${local.full_suffix}-app-sg-"
  description = "Security group for backend application - Railway to RDS/VPC endpoints"
  vpc_id      = var.vpc_id

  tags = merge(
    local.common_tags,
    {
      Name    = "${local.full_suffix}-app-security-group"
      Purpose = "Backend-Application"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# Ingress rule: Allow HTTPS from Railway IP ranges
# Conditional: Only create if Railway IP ranges are provided
resource "aws_security_group_rule" "app_ingress_from_railway" {
  count             = length(var.railway_ip_ranges) > 0 ? length(var.railway_ip_ranges) : 0
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = [var.railway_ip_ranges[count.index]]
  security_group_id = aws_security_group.app.id
  description       = "Allow HTTPS from Railway IP range ${count.index + 1}"
}

# Egress rule: Allow PostgreSQL to RDS security group
resource "aws_security_group_rule" "app_egress_to_rds" {
  type                     = "egress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.rds.id
  security_group_id        = aws_security_group.app.id
  description              = "Allow PostgreSQL connections to RDS security group"
}

# Egress rule: Allow HTTPS to VPC endpoint security group
resource "aws_security_group_rule" "app_egress_to_vpc_endpoints" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.vpc_endpoints.id
  security_group_id        = aws_security_group.app.id
  description              = "Allow HTTPS to VPC endpoints (S3, Bedrock)"
}

# ------------------------------------------------------------------------------
# VPC Endpoint Security Group
# ------------------------------------------------------------------------------
# Ingress: HTTPS (443) from application security group
# Egress: HTTPS (443) to internet for AWS service communication
# ------------------------------------------------------------------------------

resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "${local.full_suffix}-vpc-endpoint-sg-"
  description = "Security group for VPC interface endpoints - allows HTTPS from application"
  vpc_id      = var.vpc_id

  tags = merge(
    local.common_tags,
    {
      Name    = "${local.full_suffix}-vpc-endpoint-security-group"
      Purpose = "VPC-Endpoints"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# Ingress rule: Allow HTTPS from application security group
resource "aws_security_group_rule" "vpc_endpoints_ingress_from_app" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.app.id
  security_group_id        = aws_security_group.vpc_endpoints.id
  description              = "Allow HTTPS from application security group"
}

# Egress rule: Allow HTTPS to internet for AWS service communication
resource "aws_security_group_rule" "vpc_endpoints_egress_to_internet" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.vpc_endpoints.id
  description       = "Allow HTTPS to AWS services via VPC endpoints"
}
