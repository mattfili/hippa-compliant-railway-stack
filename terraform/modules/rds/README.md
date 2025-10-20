# RDS Module

## Purpose
Provision RDS PostgreSQL instances with pgvector extension, encryption, automated backups, Multi-AZ deployment, and read replicas for HIPAA-compliant database infrastructure.

## Status
Fully Implemented

## Features

- **PostgreSQL 15.x with pgvector Extension**: Enables vector embeddings for AI/ML workloads
- **KMS Encryption at Rest**: Uses customer-managed KMS keys for data encryption
- **Multi-AZ Deployment**: High availability across multiple availability zones (optional)
- **Read Replicas**: Scale read operations with replica instances (production)
- **Automated Backups**: 30-day retention with point-in-time recovery
- **Enhanced Monitoring**: OS-level metrics via CloudWatch
- **Performance Insights**: Query performance analysis (optional)
- **IAM Database Authentication**: Enhanced security for database access
- **SSL/TLS Enforcement**: Encrypted connections required
- **Manual Snapshots**: Automated snapshot creation before destructive changes (production)

## Dependencies

### Required Modules
- **VPC Module**: Requires VPC ID and private subnet IDs
- **KMS Module**: Requires KMS key ID for encryption
- **Networking Module**: Requires security group ID for access control

### External Dependencies
- AWS Provider (>= 5.0)
- Random Provider (for password generation)
- Null Provider (for manual snapshots)

## Critical Configuration: pgvector Extension

The pgvector extension is **CRITICAL** for this application. It is enabled via the DB parameter group:

```hcl
parameter {
  name         = "shared_preload_libraries"
  value        = "vector"
  apply_method = "pending-reboot"
}
```

After RDS instance creation, you must enable the extension in your database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Verify the extension is installed:

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

## Input Variables

### Required Variables

| Variable | Type | Description |
|----------|------|-------------|
| `environment` | string | Environment name (dev, staging, production) |
| `vpc_id` | string | VPC ID from vpc module |
| `private_subnet_ids` | list(string) | Private subnet IDs for RDS (minimum 2 required) |
| `security_group_id` | string | Security group ID for RDS access control |
| `kms_key_id` | string | KMS key ID for RDS encryption |

### Optional Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `instance_class` | string | `db.t3.medium` | RDS instance type |
| `allocated_storage` | number | `20` | Initial storage in GB |
| `max_allocated_storage` | number | `100` | Maximum storage for autoscaling |
| `multi_az` | bool | `false` | Enable Multi-AZ deployment |
| `enable_read_replica` | bool | `false` | Enable read replica (production only) |
| `backup_retention_days` | number | `30` | Backup retention period (1-35 days) |
| `deletion_protection` | bool | `false` | Prevent accidental deletion |
| `db_name` | string | `hipaa_db` | Initial database name |
| `db_username` | string | `admin_user` | Master username |
| `db_port` | number | `5432` | PostgreSQL port |
| `engine_version` | string | `15.7` | PostgreSQL version (15.x) |
| `enable_performance_insights` | bool | `false` | Enable Performance Insights |
| `enable_enhanced_monitoring` | bool | `true` | Enable Enhanced Monitoring |
| `enable_cloudwatch_logs` | bool | `true` | Export logs to CloudWatch |
| `enable_iam_database_authentication` | bool | `true` | Enable IAM DB authentication |

See `variables.tf` for complete list and validation rules.

## Output Values

### Primary Outputs

| Output | Description | Sensitive |
|--------|-------------|-----------|
| `rds_endpoint` | Primary endpoint (host:port) | No |
| `rds_address` | Primary instance hostname | No |
| `rds_port` | Database port | No |
| `rds_db_name` | Database name | No |
| `rds_username` | Master username | Yes |
| `rds_password` | Master password | Yes |
| `rds_arn` | Instance ARN | No |
| `connection_string` | Full PostgreSQL connection string | Yes |
| `connection_string_asyncpg` | Connection string for Python asyncpg | Yes |

### Replica Outputs

| Output | Description |
|--------|-------------|
| `rds_reader_endpoint` | Read replica endpoint (empty if disabled) |
| `rds_reader_address` | Read replica hostname |
| `rds_reader_arn` | Read replica ARN |

### Metadata Outputs

| Output | Description |
|--------|-------------|
| `db_subnet_group_name` | Subnet group name |
| `db_parameter_group_name` | Parameter group name (includes pgvector) |
| `environment` | Environment name |
| `engine_version` | Actual PostgreSQL version |
| `storage_encrypted` | Whether encryption is enabled |
| `multi_az` | Whether Multi-AZ is enabled |

## Usage Examples

### Development Environment
```hcl
module "rds" {
  source = "./modules/rds"

  environment         = "dev"
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  security_group_id   = module.networking.rds_security_group_id
  kms_key_id          = module.kms.kms_master_key_id

  instance_class      = "db.t3.medium"
  allocated_storage   = 20
  multi_az            = false
  enable_read_replica = false
  deletion_protection = false

  tags = {
    Project = "HIPAA Compliant Stack"
  }
}
```

### Staging Environment
```hcl
module "rds" {
  source = "./modules/rds"

  environment         = "staging"
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  security_group_id   = module.networking.rds_security_group_id
  kms_key_id          = module.kms.kms_master_key_id

  instance_class      = "db.t3.large"
  allocated_storage   = 50
  multi_az            = true
  enable_read_replica = false
  deletion_protection = false

  enable_performance_insights = false

  tags = {
    Project = "HIPAA Compliant Stack"
  }
}
```

### Production Environment
```hcl
module "rds" {
  source = "./modules/rds"

  environment         = "production"
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  security_group_id   = module.networking.rds_security_group_id
  kms_key_id          = module.kms.kms_master_key_id

  instance_class      = "db.r6g.xlarge"
  allocated_storage   = 100
  max_allocated_storage = 500
  multi_az            = true
  enable_read_replica = true
  deletion_protection = true

  enable_performance_insights = true
  performance_insights_retention_days = 731
  enable_enhanced_monitoring = true
  monitoring_interval = 60

  skip_final_snapshot = false

  tags = {
    Project = "HIPAA Compliant Stack"
  }
}
```

## Environment-Specific Sizing Recommendations

| Environment | Instance Type | vCPUs | RAM | Storage | Multi-AZ | Read Replica | Monthly Cost (est.) |
|-------------|---------------|-------|-----|---------|----------|--------------|---------------------|
| Development | db.t3.medium  | 2     | 4GB | 20GB    | No       | No           | ~$60                |
| Staging     | db.t3.large   | 2     | 8GB | 50GB    | Yes      | No           | ~$120               |
| Production  | db.r6g.xlarge | 4     | 32GB| 100GB   | Yes      | Yes          | ~$350               |

## Backup Strategy

### Automated Backups
- **Retention**: 30 days (configurable 1-35 days)
- **Backup Window**: 02:00-04:00 UTC (configurable)
- **Point-in-Time Recovery**: 5-minute granularity
- **Cross-Region Replication**: Not implemented (future enhancement)

### Manual Snapshots
- **Production Only**: Automatic manual snapshot before destructive changes
- **Naming Pattern**: `manual-{environment}-hipaa-db-primary-{timestamp}`
- **Retention**: Manual (must be deleted manually)

### Snapshot Restoration
```bash
# List available snapshots
aws rds describe-db-snapshots --db-instance-identifier production-hipaa-db-primary

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier production-hipaa-db-restored \
  --db-snapshot-identifier manual-production-hipaa-db-primary-2025-10-17
```

## Password Management

The master password is generated automatically using Terraform's `random_password` resource. For production deployments:

1. **Store in AWS Secrets Manager**:
```bash
aws secretsmanager create-secret \
  --name production-rds-master-password \
  --secret-string "$(terraform output -raw rds_password)"
```

2. **Rotate Password**:
```sql
-- Connect as master user
ALTER USER admin_user WITH PASSWORD 'new_secure_password';
```

3. **Update Secrets Manager**:
```bash
aws secretsmanager update-secret \
  --secret-id production-rds-master-password \
  --secret-string "new_secure_password"
```

## Multi-AZ Configuration

Multi-AZ deployment provides:
- **Automatic Failover**: 1-2 minutes during maintenance or failure
- **Synchronous Replication**: Zero data loss
- **Different Availability Zone**: Physical redundancy
- **Automatic Backup**: Taken from standby (no performance impact)

Enable for staging and production:
```hcl
multi_az = true
```

## Read Replica Configuration

Read replicas provide:
- **Read Scaling**: Distribute read traffic across multiple instances
- **Asynchronous Replication**: Eventual consistency
- **Different AZ**: Can be in different region (not implemented)
- **Failover Target**: Can be promoted to primary

Enable for production:
```hcl
enable_read_replica = true
```

## Performance Tuning

### Parameter Group Settings
The module configures optimal PostgreSQL parameters:

- `work_mem = 16MB`: Memory for query operations
- `maintenance_work_mem = 512MB`: Memory for maintenance (VACUUM, CREATE INDEX)
- `effective_cache_size = 1GB`: Planner's cache size estimate
- `shared_preload_libraries = vector`: **CRITICAL** for pgvector extension

### Performance Insights
When enabled, provides:
- Query analysis and troubleshooting
- Wait event analysis
- Top SQL queries by load
- Historical performance data (7 or 731 days)

Production recommendation:
```hcl
enable_performance_insights = true
performance_insights_retention_days = 731
```

## Enhanced Monitoring

Provides OS-level metrics:
- CPU utilization
- Memory usage
- Disk I/O
- Network traffic
- Process list

Monitoring intervals: 1, 5, 10, 15, 30, or 60 seconds

Production recommendation:
```hcl
enable_enhanced_monitoring = true
monitoring_interval = 60
```

## CloudWatch Logs

Exports PostgreSQL logs to CloudWatch:
- `postgresql`: General PostgreSQL logs
- `upgrade`: Database upgrade logs

Query logs from CloudWatch:
```bash
aws logs tail /aws/rds/instance/production-hipaa-db-primary/postgresql --follow
```

## Security Configuration

### Encryption
- **At Rest**: KMS encryption with customer-managed key
- **In Transit**: SSL/TLS required (`rds.force_ssl = 1`)
- **Backups**: Encrypted with same KMS key
- **Snapshots**: Inherit encryption from source

### Network Security
- **Private Subnets Only**: No public accessibility
- **Security Group**: Allows PostgreSQL (5432) from app security group only
- **VPC Endpoints**: Optional for private AWS service access

### IAM Database Authentication
When enabled, users can authenticate using IAM credentials:

```bash
# Generate authentication token
export PGPASSWORD="$(aws rds generate-db-auth-token \
  --hostname production-hipaa-db-primary.xxx.us-east-1.rds.amazonaws.com \
  --port 5432 \
  --username iam_user \
  --region us-east-1)"

# Connect using IAM authentication
psql "host=production-hipaa-db-primary.xxx.us-east-1.rds.amazonaws.com \
     port=5432 dbname=hipaa_db user=iam_user sslmode=require"
```

## Maintenance Windows

### Backup Window
Default: `02:00-04:00 UTC`
- No snapshots taken during high-traffic periods
- Backups taken from standby (Multi-AZ)

### Maintenance Window
Default: `sun:04:00-sun:06:00 UTC`
- OS patches, minor version upgrades
- Low-traffic period recommended

## Cost Optimization

### Storage Autoscaling
```hcl
allocated_storage     = 100  # Initial size
max_allocated_storage = 500  # Scale up to 500GB automatically
```

### Instance Sizing
- **Development**: Use burstable instances (db.t3.*)
- **Production**: Use memory-optimized instances (db.r6g.*)

### Savings Plans
For production workloads:
- 1-year commitment: ~30% savings
- 3-year commitment: ~50% savings

### Reserved Instances
Alternative to Savings Plans:
- 1-year No Upfront: ~25% savings
- 3-year All Upfront: ~60% savings

## Troubleshooting

### pgvector Extension Not Available

**Problem**: `ERROR: extension "vector" is not available`

**Solution**:
1. Verify parameter group has `shared_preload_libraries = vector`
2. Reboot RDS instance (required for shared_preload_libraries changes)
3. Create extension: `CREATE EXTENSION vector;`

### Connection Timeout

**Problem**: Cannot connect to RDS from application

**Checklist**:
1. Verify security group allows traffic from app security group
2. Check that RDS is in private subnets
3. Verify VPC endpoints configured correctly
4. Test connectivity from app server:
```bash
psql -h rds-endpoint -U admin_user -d hipaa_db
```

### Performance Issues

**Problem**: Slow queries

**Solutions**:
1. Enable Performance Insights to identify slow queries
2. Check Enhanced Monitoring for resource bottlenecks
3. Review CloudWatch logs for connection issues
4. Adjust parameter group settings (work_mem, shared_buffers)
5. Consider upgrading instance class

### High Storage Usage

**Problem**: Storage autoscaling triggered frequently

**Solutions**:
1. Review data retention policies
2. Vacuum and analyze tables regularly
3. Archive old data to S3
4. Increase `max_allocated_storage`

## Compliance Notes

### HIPAA Requirements Addressed

- **Encryption at Rest** (164.312(a)(2)(iv)): KMS encryption enabled
- **Encryption in Transit** (164.312(e)(1)): SSL/TLS enforced
- **Access Controls** (164.312(a)(1)): IAM authentication, security groups
- **Audit Logging** (164.312(b)): CloudWatch logs, Enhanced Monitoring
- **Backup & Recovery** (164.308(a)(7)(ii)(A)): 30-day retention, point-in-time recovery

### Audit Checklist
- [ ] Storage encryption enabled (`storage_encrypted = true`)
- [ ] SSL enforcement configured (`rds.force_ssl = 1`)
- [ ] No public accessibility (`publicly_accessible = false`)
- [ ] Private subnets only
- [ ] Security group restricts access to app tier only
- [ ] Automated backups enabled (30-day retention)
- [ ] CloudWatch logs exported
- [ ] Deletion protection enabled (production)

## Known Limitations

- **Manual Password Rotation**: Password rotation must be done manually
- **Single Region**: Cross-region replication not implemented
- **Automatic Failover Testing**: Must be tested manually
- **No Secrets Manager Integration**: Passwords stored in Terraform state

## Future Enhancements

- AWS Secrets Manager integration for password rotation
- Cross-region read replicas for disaster recovery
- Automated failover testing
- Aurora PostgreSQL migration path
- Automated performance tuning recommendations
- Custom CloudWatch alarms and dashboards

## Resources Created

This module creates the following AWS resources:

1. `aws_db_subnet_group.main` - DB subnet group
2. `aws_db_parameter_group.main` - Parameter group with pgvector
3. `aws_iam_role.rds_monitoring` - Enhanced Monitoring IAM role (conditional)
4. `aws_iam_role_policy_attachment.rds_monitoring` - Role policy attachment (conditional)
5. `random_password.master_password` - Master password
6. `aws_db_instance.main` - Primary RDS instance
7. `aws_db_instance.read_replica` - Read replica instance (conditional)
8. `null_resource.manual_snapshot` - Manual snapshot trigger (production only)

## Support and Contribution

For issues or questions about this module, please refer to the main project README or create an issue in the project repository.

## License

This module is part of the HIPAA Compliant Railway Stack and follows the project's licensing terms.
