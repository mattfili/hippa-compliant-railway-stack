# ==============================================================================
# S3 Storage Module - HIPAA-Compliant Document Storage
# ==============================================================================
# This module provisions three S3 buckets for document storage, backups, and
# audit logs with encryption, versioning, lifecycle policies, and logging.
# ==============================================================================

locals {
  # Construct environment label with optional suffix for test isolation
  env_label   = var.environment
  full_suffix = var.name_suffix == "" ? local.env_label : "${local.env_label}-${var.name_suffix}"

  # Bucket naming convention: hipaa-compliant-{type}-{env_label}-{account-id}
  documents_bucket_name = var.documents_bucket_name != "" ? var.documents_bucket_name : "hipaa-compliant-docs-${local.full_suffix}-${var.aws_account_id}"
  backups_bucket_name   = "hipaa-compliant-backups-${local.full_suffix}-${var.aws_account_id}"
  audit_logs_bucket_name = "hipaa-compliant-audit-${local.full_suffix}-${var.aws_account_id}"

  common_tags = merge(
    var.tags,
    {
      Module      = "s3"
      Environment = var.environment
      Context     = var.name_suffix
      ManagedBy   = "Terraform"
    }
  )
}

# ==============================================================================
# Documents Bucket - PHI Document Storage
# ==============================================================================

resource "aws_s3_bucket" "documents" {
  bucket        = local.documents_bucket_name
  force_destroy = false

  tags = merge(
    local.common_tags,
    {
      Name    = local.documents_bucket_name
      Purpose = "PHI Document Storage"
    }
  )
}

# ==============================================================================
# Backups Bucket - Database and Application Backups
# ==============================================================================

resource "aws_s3_bucket" "backups" {
  bucket        = local.backups_bucket_name
  force_destroy = false

  tags = merge(
    local.common_tags,
    {
      Name    = local.backups_bucket_name
      Purpose = "Database and Application Backups"
    }
  )
}

# ==============================================================================
# Audit Logs Bucket - Access Logs and Compliance Audit Trail
# ==============================================================================

resource "aws_s3_bucket" "audit_logs" {
  bucket        = local.audit_logs_bucket_name
  force_destroy = false

  tags = merge(
    local.common_tags,
    {
      Name    = local.audit_logs_bucket_name
      Purpose = "Audit Logs and Compliance Trail"
    }
  )
}

# ==============================================================================
# SSE-KMS Encryption Configuration - All Buckets
# ==============================================================================

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = true
  }
}

# ==============================================================================
# Versioning Configuration - All Buckets
# ==============================================================================

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ==============================================================================
# Public Access Block - All Buckets (HIPAA Requirement)
# ==============================================================================

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ==============================================================================
# Lifecycle Policies - Documents Bucket (Cost Optimization)
# ==============================================================================

resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  count  = var.enable_lifecycle_policies ? 1 : 0
  bucket = aws_s3_bucket.documents.id

  rule {
    id     = "transition-to-infrequent-access"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555 # 7 years - HIPAA retention requirement
    }
  }

  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# ==============================================================================
# Lifecycle Policies - Backups Bucket
# ==============================================================================

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  count  = var.enable_lifecycle_policies ? 1 : 0
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "transition-backups-to-glacier"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555 # 7 years - HIPAA retention requirement
    }
  }

  rule {
    id     = "expire-noncurrent-backup-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# ==============================================================================
# Access Logging Configuration
# ==============================================================================

resource "aws_s3_bucket_logging" "documents" {
  bucket = aws_s3_bucket.documents.id

  target_bucket = aws_s3_bucket.audit_logs.id
  target_prefix = "documents-access/"
}

resource "aws_s3_bucket_logging" "backups" {
  bucket = aws_s3_bucket.backups.id

  target_bucket = aws_s3_bucket.audit_logs.id
  target_prefix = "backups-access/"
}
