# ==============================================================================
# AWS Config Module - Compliance Monitoring
# ==============================================================================
# Purpose: Deploy AWS Config for continuous HIPAA compliance monitoring
# Dependencies: Requires S3 audit logs bucket for Config snapshots
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
# IAM Role for AWS Config
# ------------------------------------------------------------------------------
resource "aws_iam_role" "config" {
  name        = "${local.full_suffix}-config-role"
  description = "IAM role for AWS Config service"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.full_suffix}-config-role"
    }
  )
}

# Attach AWS managed Config policy
resource "aws_iam_role_policy_attachment" "config_managed_policy" {
  role       = aws_iam_role.config.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/ConfigRole"
}

# Custom policy for S3 bucket access
resource "aws_iam_role_policy" "config_s3_policy" {
  name = "${local.full_suffix}-config-s3-policy"
  role = aws_iam_role.config.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "arn:aws:s3:::${var.s3_bucket_audit_logs}/*"
        Condition = {
          StringLike = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketVersioning"
        ]
        Resource = "arn:aws:s3:::${var.s3_bucket_audit_logs}"
      }
    ]
  })
}

# ------------------------------------------------------------------------------
# AWS Config Recorder
# ------------------------------------------------------------------------------
resource "aws_config_configuration_recorder" "main" {
  name     = "${local.full_suffix}-config-recorder"
  role_arn = aws_iam_role.config.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

# ------------------------------------------------------------------------------
# AWS Config Delivery Channel
# ------------------------------------------------------------------------------
resource "aws_config_delivery_channel" "main" {
  name           = "${local.full_suffix}-config-delivery-channel"
  s3_bucket_name = var.s3_bucket_audit_logs

  snapshot_delivery_properties {
    delivery_frequency = "TwentyFour_Hours"
  }

  sns_topic_arn = aws_sns_topic.config_alerts.arn

  depends_on = [aws_config_configuration_recorder.main]
}

# ------------------------------------------------------------------------------
# Start Config Recorder
# ------------------------------------------------------------------------------
resource "aws_config_configuration_recorder_status" "main" {
  name       = aws_config_configuration_recorder.main.name
  is_enabled = true

  depends_on = [aws_config_delivery_channel.main]
}

# ------------------------------------------------------------------------------
# SNS Topic for Config Alerts
# ------------------------------------------------------------------------------
resource "aws_sns_topic" "config_alerts" {
  name         = "${local.full_suffix}-config-alerts"
  display_name = "AWS Config Compliance Alerts - ${local.full_suffix}"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.full_suffix}-config-alerts"
    }
  )
}

# SNS Topic Policy to allow Config to publish
resource "aws_sns_topic_policy" "config_alerts" {
  arn = aws_sns_topic.config_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.config_alerts.arn
      }
    ]
  })
}

# SNS Email Subscription (conditional)
resource "aws_sns_topic_subscription" "config_email" {
  count     = var.sns_alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.config_alerts.arn
  protocol  = "email"
  endpoint  = var.sns_alert_email
}

# ------------------------------------------------------------------------------
# AWS Config Rules - HIPAA Compliance
# ------------------------------------------------------------------------------

# Rule 1: S3 Bucket Server-Side Encryption Enabled
resource "aws_config_config_rule" "s3_bucket_encryption" {
  name        = "${local.full_suffix}-s3-bucket-encryption-enabled"
  description = "Checks that S3 buckets have server-side encryption enabled"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"
  }

  depends_on = [aws_config_configuration_recorder_status.main]

  tags = merge(
    local.common_tags,
    {
      Name       = "${local.full_suffix}-s3-bucket-encryption-enabled"
      Compliance = "HIPAA"
    }
  )
}

# Rule 2: RDS Storage Encrypted
resource "aws_config_config_rule" "rds_storage_encrypted" {
  name        = "${local.full_suffix}-rds-storage-encrypted"
  description = "Checks that RDS instances have encryption at rest enabled"

  source {
    owner             = "AWS"
    source_identifier = "RDS_STORAGE_ENCRYPTED"
  }

  depends_on = [aws_config_configuration_recorder_status.main]

  tags = merge(
    local.common_tags,
    {
      Name       = "${local.full_suffix}-rds-storage-encrypted"
      Compliance = "HIPAA"
    }
  )
}

# Rule 3: RDS Instance Public Access Check
resource "aws_config_config_rule" "rds_public_access" {
  name        = "${local.full_suffix}-rds-instance-public-access-check"
  description = "Checks that RDS instances are not publicly accessible"

  source {
    owner             = "AWS"
    source_identifier = "RDS_INSTANCE_PUBLIC_ACCESS_CHECK"
  }

  depends_on = [aws_config_configuration_recorder_status.main]

  tags = merge(
    local.common_tags,
    {
      Name       = "${local.full_suffix}-rds-instance-public-access-check"
      Compliance = "HIPAA"
    }
  )
}

# Rule 4: IAM Policy No Statements With Admin Access
resource "aws_config_config_rule" "iam_policy_no_admin_access" {
  name        = "${local.full_suffix}-iam-policy-no-admin-access"
  description = "Checks that IAM policies do not grant full administrative privileges"

  source {
    owner             = "AWS"
    source_identifier = "IAM_POLICY_NO_STATEMENTS_WITH_ADMIN_ACCESS"
  }

  depends_on = [aws_config_configuration_recorder_status.main]

  tags = merge(
    local.common_tags,
    {
      Name       = "${local.full_suffix}-iam-policy-no-admin-access"
      Compliance = "HIPAA"
    }
  )
}

# Rule 5: CloudTrail Enabled
resource "aws_config_config_rule" "cloudtrail_enabled" {
  name        = "${local.full_suffix}-cloudtrail-enabled"
  description = "Checks that CloudTrail is enabled for audit logging"

  source {
    owner             = "AWS"
    source_identifier = "CLOUD_TRAIL_ENABLED"
  }

  depends_on = [aws_config_configuration_recorder_status.main]

  tags = merge(
    local.common_tags,
    {
      Name       = "${local.full_suffix}-cloudtrail-enabled"
      Compliance = "HIPAA"
    }
  )
}

# Rule 6: VPC Security Group Open Only to Authorized Ports
resource "aws_config_config_rule" "vpc_sg_authorized_ports" {
  name        = "${local.full_suffix}-vpc-sg-open-authorized-ports"
  description = "Checks that security groups do not allow unrestricted access"

  source {
    owner             = "AWS"
    source_identifier = "VPC_SG_OPEN_ONLY_TO_AUTHORIZED_PORTS"
  }

  scope {
    compliance_resource_types = ["AWS::EC2::SecurityGroup"]
  }

  input_parameters = jsonencode({
    authorizedTcpPorts = "443,5432"
  })

  depends_on = [aws_config_configuration_recorder_status.main]

  tags = merge(
    local.common_tags,
    {
      Name       = "${local.full_suffix}-vpc-sg-open-authorized-ports"
      Compliance = "HIPAA"
    }
  )
}
