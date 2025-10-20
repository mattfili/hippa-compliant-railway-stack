# RDS Module - Input Variables

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, production)"
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production"
  }
}

variable "vpc_id" {
  type        = string
  description = "VPC ID from vpc module"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for RDS deployment"
  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "At least 2 private subnets are required for RDS subnet group"
  }
}

variable "security_group_id" {
  type        = string
  description = "Security group ID for RDS access control"
}

variable "kms_key_id" {
  type        = string
  description = "KMS key ID for RDS encryption"
}

variable "instance_class" {
  type        = string
  description = "RDS instance type"
  default     = "db.t3.medium"
  validation {
    condition     = can(regex("^db\\.", var.instance_class))
    error_message = "Instance class must start with 'db.'"
  }
}

variable "allocated_storage" {
  type        = number
  description = "Allocated storage in GB"
  default     = 20
  validation {
    condition     = var.allocated_storage >= 20
    error_message = "Allocated storage must be at least 20 GB"
  }
}

variable "max_allocated_storage" {
  type        = number
  description = "Maximum allocated storage for autoscaling in GB"
  default     = 100
  validation {
    condition     = var.max_allocated_storage >= var.allocated_storage
    error_message = "Max allocated storage must be greater than or equal to allocated storage"
  }
}

variable "multi_az" {
  type        = bool
  description = "Enable Multi-AZ deployment for high availability"
  default     = false
}

variable "enable_read_replica" {
  type        = bool
  description = "Enable read replica (production only)"
  default     = false
}

variable "backup_retention_days" {
  type        = number
  description = "Automated backup retention period in days"
  default     = 30
  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 35
    error_message = "Backup retention days must be between 1 and 35"
  }
}

variable "deletion_protection" {
  type        = bool
  description = "Enable deletion protection to prevent accidental database deletion"
  default     = false
}

variable "db_name" {
  type        = string
  description = "Name of the initial database to create"
  default     = "hipaa_db"
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]*$", var.db_name))
    error_message = "Database name must start with a letter and contain only alphanumeric characters and underscores"
  }
}

variable "db_username" {
  type        = string
  description = "Master username for the database"
  default     = "admin_user"
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]*$", var.db_username))
    error_message = "Username must start with a letter and contain only alphanumeric characters and underscores"
  }
}

variable "db_port" {
  type        = number
  description = "Port for PostgreSQL database"
  default     = 5432
}

variable "engine_version" {
  type        = string
  description = "PostgreSQL engine version"
  default     = "15.7"
  validation {
    condition     = can(regex("^15\\.", var.engine_version))
    error_message = "Engine version must be PostgreSQL 15.x"
  }
}

variable "parameter_group_family" {
  type        = string
  description = "PostgreSQL parameter group family"
  default     = "postgres15"
}

variable "backup_window" {
  type        = string
  description = "Preferred backup window (UTC)"
  default     = "02:00-04:00"
  validation {
    condition     = can(regex("^([0-1][0-9]|2[0-3]):[0-5][0-9]-([0-1][0-9]|2[0-3]):[0-5][0-9]$", var.backup_window))
    error_message = "Backup window must be in format HH:MM-HH:MM"
  }
}

variable "maintenance_window" {
  type        = string
  description = "Preferred maintenance window (UTC)"
  default     = "sun:04:00-sun:06:00"
  validation {
    condition     = can(regex("^(mon|tue|wed|thu|fri|sat|sun):[0-9]{2}:[0-9]{2}-(mon|tue|wed|thu|fri|sat|sun):[0-9]{2}:[0-9]{2}$", var.maintenance_window))
    error_message = "Maintenance window must be in format ddd:HH:MM-ddd:HH:MM"
  }
}

variable "enable_performance_insights" {
  type        = bool
  description = "Enable Performance Insights for query analysis"
  default     = false
}

variable "performance_insights_retention_days" {
  type        = number
  description = "Performance Insights data retention in days (7 for free tier, 731 max)"
  default     = 7
  validation {
    condition     = contains([7, 731], var.performance_insights_retention_days)
    error_message = "Performance Insights retention must be 7 (free) or 731 days"
  }
}

variable "enable_enhanced_monitoring" {
  type        = bool
  description = "Enable Enhanced Monitoring for OS-level metrics"
  default     = true
}

variable "monitoring_interval" {
  type        = number
  description = "Enhanced Monitoring interval in seconds (0, 1, 5, 10, 15, 30, 60)"
  default     = 60
  validation {
    condition     = contains([0, 1, 5, 10, 15, 30, 60], var.monitoring_interval)
    error_message = "Monitoring interval must be 0, 1, 5, 10, 15, 30, or 60 seconds"
  }
}

variable "enable_cloudwatch_logs" {
  type        = bool
  description = "Enable CloudWatch log exports"
  default     = true
}

variable "cloudwatch_log_types" {
  type        = list(string)
  description = "PostgreSQL log types to export to CloudWatch"
  default     = ["postgresql", "upgrade"]
  validation {
    condition     = alltrue([for log_type in var.cloudwatch_log_types : contains(["postgresql", "upgrade"], log_type)])
    error_message = "Log types must be 'postgresql' and/or 'upgrade'"
  }
}

variable "enable_iam_database_authentication" {
  type        = bool
  description = "Enable IAM database authentication for enhanced security"
  default     = true
}

variable "skip_final_snapshot" {
  type        = bool
  description = "Skip final snapshot when deleting database (set to false for production)"
  default     = false
}

variable "final_snapshot_identifier_prefix" {
  type        = string
  description = "Prefix for final snapshot identifier"
  default     = "final-snapshot"
}

variable "copy_tags_to_snapshot" {
  type        = bool
  description = "Copy tags to snapshots"
  default     = true
}

variable "auto_minor_version_upgrade" {
  type        = bool
  description = "Enable automatic minor version upgrades"
  default     = true
}

variable "apply_immediately" {
  type        = bool
  description = "Apply changes immediately instead of during maintenance window"
  default     = false
}

variable "tags" {
  type        = map(string)
  description = "Additional resource tags"
  default     = {}
}
