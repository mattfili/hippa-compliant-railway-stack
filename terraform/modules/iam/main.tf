# ==============================================================================
# IAM Module - Least-Privilege Access Control
# ==============================================================================
# This module provisions IAM roles and policies for the backend application
# with strict least-privilege access to S3, KMS, RDS, and Bedrock services.
# ==============================================================================

locals {
  # Construct environment label with optional suffix for test isolation
  env_label   = var.environment
  full_suffix = var.name_suffix == "" ? local.env_label : "${local.env_label}-${var.name_suffix}"

  role_name = "hipaa-app-backend-${local.full_suffix}"

  common_tags = merge(
    var.tags,
    {
      Module      = "iam"
      Environment = var.environment
      Context     = var.name_suffix
      ManagedBy   = "Terraform"
    }
  )
}

# ==============================================================================
# Backend Application IAM Role
# ==============================================================================

resource "aws_iam_role" "backend_app" {
  name                 = local.role_name
  description          = "IAM role for HIPAA-compliant backend application in ${local.full_suffix} environment"
  max_session_duration = 3600

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.external_id
          }
        }
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = local.role_name
    }
  )
}

# ==============================================================================
# Data Sources
# ==============================================================================

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# ==============================================================================
# S3 Access Policy - Least Privilege
# ==============================================================================

resource "aws_iam_policy" "s3_access" {
  name        = "${local.full_suffix}-s3-access-policy"
  description = "Least-privilege S3 access for backend application in ${local.full_suffix}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListDocumentsBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_documents_arn
        ]
        Condition = {
          StringLike = {
            "s3:prefix" = [
              "tenants/*"
            ]
          }
        }
      },
      {
        Sid    = "ManageDocumentsInTenantFolders"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${var.s3_bucket_documents_arn}/tenants/*"
        ]
      },
      {
        Sid    = "ListBackupsBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_backups_arn
        ]
      },
      {
        Sid    = "WriteBackups"
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          "${var.s3_bucket_backups_arn}/*"
        ]
      },
      {
        Sid    = "ListAuditLogsBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_audit_logs_arn
        ]
      },
      {
        Sid    = "AppendAuditLogs"
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          "${var.s3_bucket_audit_logs_arn}/application-logs/*"
        ]
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.full_suffix}-s3-access-policy"
    }
  )
}

# ==============================================================================
# KMS Access Policy - Encryption Operations
# ==============================================================================

resource "aws_iam_policy" "kms_access" {
  name        = "${local.full_suffix}-kms-access-policy"
  description = "KMS encryption operations for backend application in ${local.full_suffix}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "UseMasterKey"
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = [
          var.kms_master_key_arn
        ]
      },
      {
        Sid    = "CreateTenantKeys"
        Effect = "Allow"
        Action = [
          "kms:CreateKey",
          "kms:TagResource"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = data.aws_region.current.name
          }
        }
      },
      {
        Sid    = "ManageTenantKeys"
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey",
          "kms:EnableKeyRotation",
          "kms:GetKeyRotationStatus"
        ]
        Resource = "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:key/*"
        Condition = {
          StringEquals = {
            "kms:ResourceTag/Environment" = var.environment
            "kms:ResourceTag/ManagedBy"   = "Application"
          }
        }
      },
      {
        Sid    = "ListKeys"
        Effect = "Allow"
        Action = [
          "kms:ListKeys",
          "kms:ListAliases"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.full_suffix}-kms-access-policy"
    }
  )
}

# ==============================================================================
# Bedrock Access Policy - AI Model Invocation
# ==============================================================================

resource "aws_iam_policy" "bedrock_access" {
  name        = "${local.full_suffix}-bedrock-access-policy"
  description = "Amazon Bedrock model invocation for backend application in ${local.full_suffix}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeClaudeModels"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/anthropic.claude-*"
        ]
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.full_suffix}-bedrock-access-policy"
    }
  )
}

# ==============================================================================
# RDS Enhanced Monitoring Role (Conditional)
# ==============================================================================

resource "aws_iam_role" "rds_monitoring" {
  count       = var.enable_rds_monitoring ? 1 : 0
  name        = "${local.full_suffix}-rds-monitoring-role"
  description = "IAM role for RDS Enhanced Monitoring in ${local.full_suffix}"

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

  tags = merge(
    local.common_tags,
    {
      Name = "${local.full_suffix}-rds-monitoring-role"
    }
  )
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count      = var.enable_rds_monitoring ? 1 : 0
  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ==============================================================================
# Policy Attachments to Backend Application Role
# ==============================================================================

resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.backend_app.name
  policy_arn = aws_iam_policy.s3_access.arn
}

resource "aws_iam_role_policy_attachment" "kms_access" {
  role       = aws_iam_role.backend_app.name
  policy_arn = aws_iam_policy.kms_access.arn
}

resource "aws_iam_role_policy_attachment" "bedrock_access" {
  role       = aws_iam_role.backend_app.name
  policy_arn = aws_iam_policy.bedrock_access.arn
}
