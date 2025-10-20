# RDS Module - Main Configuration
# This module provisions RDS PostgreSQL with pgvector, encryption, backups, and Multi-AZ

locals {
  identifier_prefix = "${var.environment}-hipaa-db"

  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      Module      = "rds"
      ManagedBy   = "Terraform"
    }
  )
}

# ==============================================================================
# DB Subnet Group
# ==============================================================================
# Subnet group for RDS deployment in private subnets
resource "aws_db_subnet_group" "main" {
  name        = "${local.identifier_prefix}-subnet-group"
  description = "Subnet group for ${var.environment} RDS instance in private subnets"
  subnet_ids  = var.private_subnet_ids

  tags = merge(
    local.common_tags,
    {
      Name = "${local.identifier_prefix}-subnet-group"
    }
  )
}

# ==============================================================================
# DB Parameter Group with pgvector Extension
# ==============================================================================
# Parameter group enabling pgvector extension and optimal PostgreSQL settings
resource "aws_db_parameter_group" "main" {
  name        = "${local.identifier_prefix}-postgres15-pgvector"
  family      = var.parameter_group_family
  description = "Custom parameter group for ${var.environment} with pgvector extension enabled"

  # CRITICAL: Enable pgvector extension via shared_preload_libraries
  parameter {
    name         = "shared_preload_libraries"
    value        = "vector"
    apply_method = "pending-reboot"
  }

  # Performance tuning parameters
  parameter {
    name         = "work_mem"
    value        = "16384" # 16MB for query operations
    apply_method = "immediate"
  }

  parameter {
    name         = "maintenance_work_mem"
    value        = "524288" # 512MB for maintenance operations
    apply_method = "immediate"
  }

  parameter {
    name         = "effective_cache_size"
    value        = "1048576" # 1GB cache estimate
    apply_method = "immediate"
  }

  # Enable query logging for debugging (can be disabled in production)
  parameter {
    name         = "log_min_duration_statement"
    value        = "1000" # Log queries taking more than 1 second
    apply_method = "immediate"
  }

  parameter {
    name         = "log_connections"
    value        = "1"
    apply_method = "immediate"
  }

  parameter {
    name         = "log_disconnections"
    value        = "1"
    apply_method = "immediate"
  }

  # Security settings
  parameter {
    name         = "ssl"
    value        = "1"
    apply_method = "immediate"
  }

  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "immediate"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.identifier_prefix}-postgres15-pgvector"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# ==============================================================================
# IAM Role for Enhanced Monitoring (if enabled)
# ==============================================================================
resource "aws_iam_role" "rds_monitoring" {
  count = var.enable_enhanced_monitoring && var.monitoring_interval > 0 ? 1 : 0

  name        = "${local.identifier_prefix}-rds-monitoring-role"
  description = "IAM role for RDS Enhanced Monitoring in ${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count = var.enable_enhanced_monitoring && var.monitoring_interval > 0 ? 1 : 0

  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ==============================================================================
# Random Password for RDS Master User
# ==============================================================================
# Generate a secure random password for the master user
# In production, this should be stored in AWS Secrets Manager
resource "random_password" "master_password" {
  length  = 32
  special = true
  # Exclude characters that might cause issues in connection strings
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# ==============================================================================
# RDS PostgreSQL Primary Instance
# ==============================================================================
resource "aws_db_instance" "main" {
  # Instance identification
  identifier = "${local.identifier_prefix}-primary"

  # Engine configuration
  engine                      = "postgres"
  engine_version              = var.engine_version
  auto_minor_version_upgrade  = var.auto_minor_version_upgrade
  allow_major_version_upgrade = false

  # Instance sizing
  instance_class        = var.instance_class
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = var.kms_key_id

  # Database configuration
  db_name  = var.db_name
  port     = var.db_port
  username = var.db_username
  password = random_password.master_password.result

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.security_group_id]
  publicly_accessible    = false
  multi_az               = var.multi_az

  # Parameter and option groups
  parameter_group_name = aws_db_parameter_group.main.name

  # Backup configuration
  backup_retention_period   = var.backup_retention_days
  backup_window             = var.backup_window
  copy_tags_to_snapshot     = var.copy_tags_to_snapshot
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.final_snapshot_identifier_prefix}-${local.identifier_prefix}-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  delete_automated_backups  = false

  # Maintenance configuration
  maintenance_window  = var.maintenance_window
  apply_immediately   = var.apply_immediately
  deletion_protection = var.deletion_protection

  # Monitoring and logging
  enabled_cloudwatch_logs_exports = var.enable_cloudwatch_logs ? var.cloudwatch_log_types : []
  monitoring_interval             = var.enable_enhanced_monitoring ? var.monitoring_interval : 0
  monitoring_role_arn             = var.enable_enhanced_monitoring && var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null

  # Performance Insights
  performance_insights_enabled          = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? var.performance_insights_retention_days : null
  performance_insights_kms_key_id       = var.enable_performance_insights ? var.kms_key_id : null

  # IAM authentication
  iam_database_authentication_enabled = var.enable_iam_database_authentication

  tags = merge(
    local.common_tags,
    {
      Name     = "${local.identifier_prefix}-primary"
      Role     = "primary"
      Snapshot = "automated"
    }
  )

  lifecycle {
    ignore_changes = [
      # Ignore password changes after creation
      password,
      # Ignore snapshot identifier timestamp changes
      final_snapshot_identifier
    ]
  }

  depends_on = [
    aws_db_subnet_group.main,
    aws_db_parameter_group.main
  ]
}

# ==============================================================================
# RDS Read Replica (Conditional - Production Only)
# ==============================================================================
resource "aws_db_instance" "read_replica" {
  count = var.enable_read_replica ? 1 : 0

  # Instance identification
  identifier = "${local.identifier_prefix}-replica"

  # Replica configuration
  replicate_source_db = aws_db_instance.main.identifier

  # Instance sizing (can be different from primary)
  instance_class             = var.instance_class
  auto_minor_version_upgrade = var.auto_minor_version_upgrade

  # Storage configuration (inherited from primary but can be modified)
  storage_type          = "gp3"
  max_allocated_storage = var.max_allocated_storage

  # Network configuration
  publicly_accessible    = false
  vpc_security_group_ids = [var.security_group_id]

  # Parameter group (use same as primary)
  parameter_group_name = aws_db_parameter_group.main.name

  # Maintenance configuration
  maintenance_window = var.maintenance_window
  apply_immediately  = var.apply_immediately

  # Monitoring and logging
  enabled_cloudwatch_logs_exports = var.enable_cloudwatch_logs ? var.cloudwatch_log_types : []
  monitoring_interval             = var.enable_enhanced_monitoring ? var.monitoring_interval : 0
  monitoring_role_arn             = var.enable_enhanced_monitoring && var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null

  # Performance Insights
  performance_insights_enabled          = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? var.performance_insights_retention_days : null
  performance_insights_kms_key_id       = var.enable_performance_insights ? var.kms_key_id : null

  # IAM authentication
  iam_database_authentication_enabled = var.enable_iam_database_authentication

  # Backup configuration (replicas don't have automated backups)
  backup_retention_period = 0
  skip_final_snapshot     = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.identifier_prefix}-replica"
      Role = "read-replica"
    }
  )

  depends_on = [
    aws_db_instance.main
  ]
}

# ==============================================================================
# Manual Snapshot Before Destructive Changes (Production Only)
# ==============================================================================
# Create manual snapshot before destructive operations
resource "null_resource" "manual_snapshot" {
  count = var.environment == "production" ? 1 : 0

  triggers = {
    db_instance_id = aws_db_instance.main.id
    timestamp      = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Create manual snapshot before destructive changes
      aws rds create-db-snapshot \
        --db-instance-identifier ${aws_db_instance.main.identifier} \
        --db-snapshot-identifier manual-${aws_db_instance.main.identifier}-${formatdate("YYYY-MM-DD-hhmm", timestamp())} \
        --tags Key=Environment,Value=${var.environment} Key=Type,Value=manual-snapshot Key=ManagedBy,Value=Terraform
    EOT

    on_failure = continue
  }

  depends_on = [
    aws_db_instance.main
  ]
}
