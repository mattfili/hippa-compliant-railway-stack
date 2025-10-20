# ==============================================================================
# Root Terraform Configuration
# ==============================================================================
# Orchestrates all infrastructure modules for HIPAA-compliant AWS environment
# ==============================================================================

# ------------------------------------------------------------------------------
# Data Sources
# ------------------------------------------------------------------------------

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# ------------------------------------------------------------------------------
# Local Values
# ------------------------------------------------------------------------------

locals {
  # Common tags applied to all resources
  common_tags = merge(
    var.tags,
    {
      Name        = "hipaa-compliant-${var.environment}"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Project     = "HIPAA-Compliant-Document-Management"
      Workspace   = terraform.workspace
      CreatedAt   = timestamp()
    }
  )

  # Account and region information
  aws_account_id = data.aws_caller_identity.current.account_id
  aws_region     = data.aws_region.current.name
}

# ------------------------------------------------------------------------------
# Module: VPC & Networking
# ------------------------------------------------------------------------------
# Provisions VPC, subnets, routing, NAT gateways, and VPC endpoints
# No dependencies - foundational module

module "vpc" {
  source = "./modules/vpc"

  vpc_cidr             = var.vpc_cidr
  environment          = var.environment
  name_suffix          = var.name_suffix
  availability_zones   = var.availability_zones
  enable_nat_gateway   = var.enable_nat_gateway
  enable_vpc_endpoints = var.enable_vpc_endpoints
  tags                 = local.common_tags
}

# ------------------------------------------------------------------------------
# Module: KMS Encryption
# ------------------------------------------------------------------------------
# Provisions KMS master key for infrastructure encryption
# No dependencies - foundational module

module "kms" {
  source = "./modules/kms"

  environment         = var.environment
  name_suffix         = var.name_suffix
  aws_account_id      = local.aws_account_id
  enable_key_rotation = var.enable_key_rotation
  tags                = local.common_tags
}

# ------------------------------------------------------------------------------
# Module: Security Groups
# ------------------------------------------------------------------------------
# Configures security groups with least-privilege rules
# Depends on: VPC module

module "networking" {
  source = "./modules/networking"

  environment       = var.environment
  name_suffix       = var.name_suffix
  vpc_id            = module.vpc.vpc_id
  railway_ip_ranges = var.railway_ip_ranges
  tags              = local.common_tags

  depends_on = [module.vpc]
}

# ------------------------------------------------------------------------------
# Module: S3 Storage
# ------------------------------------------------------------------------------
# Provisions S3 buckets for documents, backups, and audit logs
# Depends on: KMS module

module "s3" {
  source = "./modules/s3"

  environment               = var.environment
  name_suffix               = var.name_suffix
  aws_account_id            = local.aws_account_id
  kms_key_id                = module.kms.kms_master_key_id
  enable_lifecycle_policies = var.enable_lifecycle_policies
  documents_bucket_name     = var.documents_bucket_name
  tags                      = local.common_tags

  depends_on = [module.kms]
}

# ------------------------------------------------------------------------------
# Module: RDS Database
# ------------------------------------------------------------------------------
# Provisions RDS PostgreSQL with pgvector, encryption, and backups
# Depends on: VPC, Security Groups, KMS modules

module "rds" {
  source = "./modules/rds"

  environment           = var.environment
  private_subnet_ids    = module.vpc.private_subnet_ids
  security_group_id     = module.networking.rds_security_group_id
  kms_key_id            = module.kms.kms_master_key_id
  instance_class        = var.rds_instance_class
  allocated_storage     = var.rds_allocated_storage
  multi_az              = var.rds_multi_az
  enable_read_replica   = var.enable_read_replica
  backup_retention_days = var.backup_retention_days
  deletion_protection   = var.deletion_protection
  tags                  = local.common_tags

  depends_on = [module.vpc, module.networking, module.kms]
}

# ------------------------------------------------------------------------------
# Module: IAM Access Control
# ------------------------------------------------------------------------------
# Provisions IAM roles and policies for backend application
# Depends on: S3, KMS, RDS modules

module "iam" {
  source = "./modules/iam"

  environment              = var.environment
  name_suffix              = var.name_suffix
  s3_bucket_documents_arn  = module.s3.s3_bucket_documents_arn
  s3_bucket_backups_arn    = module.s3.s3_bucket_backups_arn
  s3_bucket_audit_logs_arn = module.s3.s3_bucket_audit_logs_arn
  kms_master_key_arn       = module.kms.kms_master_key_arn
  tags                     = local.common_tags

  depends_on = [module.s3, module.kms, module.rds]
}

# ------------------------------------------------------------------------------
# Module: AWS Config Compliance
# ------------------------------------------------------------------------------
# Deploys AWS Config for continuous compliance monitoring
# Depends on: S3 module

module "config" {
  source = "./modules/config"

  environment          = var.environment
  name_suffix          = var.name_suffix
  s3_bucket_audit_logs = module.s3.s3_bucket_audit_logs
  sns_alert_email      = var.sns_alert_email
  tags                 = local.common_tags

  depends_on = [module.s3]
}
