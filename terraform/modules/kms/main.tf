# ==============================================================================
# KMS Module - Main Configuration
# ==============================================================================
# Purpose: Provision KMS master key for infrastructure encryption with
#          automatic rotation and least-privilege key policy
# ==============================================================================

locals {
  # Construct environment label with optional suffix for test isolation
  env_label   = var.environment
  full_suffix = var.name_suffix == "" ? local.env_label : "${local.env_label}-${var.name_suffix}"
}

# ------------------------------------------------------------------------------
# KMS Master Key
# ------------------------------------------------------------------------------
resource "aws_kms_key" "master" {
  description             = "HIPAA infrastructure master encryption key for ${local.full_suffix}"
  deletion_window_in_days = 30
  enable_key_rotation     = var.enable_key_rotation
  multi_region            = false

  # Key policy granting least-privilege access
  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "hipaa-master-key-policy-${local.full_suffix}"
    Statement = [
      # Root account full access (required by AWS)
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.aws_account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      # CloudTrail logging for key usage
      {
        Sid    = "Allow CloudTrail to encrypt logs"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action = [
          "kms:GenerateDataKey*",
          "kms:DecryptDataKey"
        ]
        Resource = "*"
        Condition = {
          StringLike = {
            "kms:EncryptionContext:aws:cloudtrail:arn" = "arn:aws:cloudtrail:*:${var.aws_account_id}:trail/*"
          }
        }
      },
      # RDS service access for database encryption
      {
        Sid    = "Allow RDS to use the key"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
        Action = [
          "kms:DescribeKey",
          "kms:CreateGrant"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "rds.amazonaws.com"
          }
        }
      },
      # S3 service access for bucket encryption
      {
        Sid    = "Allow S3 to use the key"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "hipaa-master-key-${var.environment}"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Purpose     = "Infrastructure encryption master key"
    }
  )
}

# ------------------------------------------------------------------------------
# KMS Key Alias
# ------------------------------------------------------------------------------
resource "aws_kms_alias" "master" {
  name          = "alias/hipaa-master-${var.environment}"
  target_key_id = aws_kms_key.master.key_id
}
