# Railway Template - What's Automated

This Railway template **automates infrastructure provisioning and application deployment**. This guide explains the Railway orchestration layer and what happens automatically during deployment.

## Architecture Overview

Railway serves as the **orchestrator** in this scaffold:
- **Hosts**: Stateless FastAPI backend containers (no PHI storage)
- **Automates**: Terraform execution to provision AWS infrastructure
- **Connects**: Application containers to AWS VPC via secure networking

AWS serves as the **data plane** where all PHI resides:
- **RDS PostgreSQL** with pgvector (provisioned via Terraform)
- **S3** encrypted document storage (provisioned via Terraform)
- **KMS** per-tenant encryption keys (provisioned via Terraform)
- **VPC** networking with security groups (provisioned via Terraform)

## What the Template Does Automatically

When you deploy the Railway template, it automatically:

### Infrastructure Provisioning (via Terraform)
✅ **Executes Terraform** to provision AWS VPC, RDS, S3, KMS, IAM roles, security groups
✅ **Creates VPC networking** for secure connectivity between Railway and AWS
✅ **Provisions RDS PostgreSQL 15** with pgvector extension, Multi-AZ, encryption
✅ **Creates S3 buckets** with encryption, versioning, bucket policies
✅ **Generates KMS keys** master key for infrastructure (per-tenant keys added on tenant creation)
✅ **Configures IAM roles** with least privilege for application access to RDS/S3/KMS
✅ **Sets up security groups** restricting database access to application only

### Application Deployment (Railway-hosted)
✅ **Deploys FastAPI backend** with automated Docker build to Railway containers
✅ **Runs database migrations** on startup (7 migrations currently)
✅ **Seeds system tenant** with ID `00000000-0000-0000-0000-000000000000`
✅ **Enables Row-Level Security** policies on all tables
✅ **Creates vector indexes** for pgvector similarity search
✅ **Configures health checks** for monitoring and automated restarts
✅ **Injects environment variables** DATABASE_URL (from Terraform output), AWS credentials, OIDC config

### Security & Networking
✅ **Enforces TLS 1.2+** encryption on all connections (RDS, S3, Bedrock)
✅ **Configures VPC peering/PrivateLink** for private connectivity (no public internet transit)
✅ **Restricts IAM permissions** application can only access specific RDS/S3/KMS resources

**You only need to**: Add your AWS credentials (for Terraform) and OIDC credentials (for authentication) in Railway dashboard after deployment.

## Prerequisites for HIPAA Production

- **AWS Account** with BAA signed for all services (RDS, S3, KMS, Bedrock, VPC, CloudWatch, CloudTrail)
- **AWS Credentials** with permissions to create infrastructure (VPC, RDS, S3, KMS, IAM) - Railway needs these to run Terraform
- **Railway Pro Plan** (for production resources and BAA eligibility - covers Railway platform only, not data services)
- **Business Associate Agreement (BAA)** signed with Railway (covers application hosting)
- **OIDC/SAML Provider** (AWS Cognito, Okta, Auth0, Azure AD) for authentication

**Note**: AWS BAA covers data services where PHI resides (RDS, S3, KMS). Railway BAA covers application hosting (stateless containers).

## Template Deployment (Recommended)

### One-Click Deploy

1. Click the "Deploy on Railway" button in README
2. Add AWS credentials in Railway dashboard (for Terraform execution)
3. Add OIDC credentials in Railway dashboard (for authentication)
4. Railway automatically provisions AWS infrastructure + deploys application (5-10 minutes)
5. Done!

### What Happens Behind the Scenes

The template uses `railway.json` which defines:

```json
{
  "services": [
    {
      "name": "terraform",
      "postDeploy": "terraform init && terraform apply -auto-approve",
      "environment": {
        "AWS_ACCESS_KEY_ID": "$AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY": "$AWS_SECRET_ACCESS_KEY",
        "AWS_REGION": "us-east-1"
      }
    },
    {
      "name": "backend",
      "buildCommand": "docker build",
      "startCommand": "sh scripts/startup.sh",  // Runs migrations + starts app
      "healthcheck": "/api/v1/health/ready",
      "environment": {
        "DATABASE_URL": "$TERRAFORM_OUTPUT_RDS_URL",  // From Terraform
        "S3_BUCKET": "$TERRAFORM_OUTPUT_S3_BUCKET",
        "KMS_KEY_ID": "$TERRAFORM_OUTPUT_KMS_KEY"
      }
    }
  ]
}
```

Railway orchestrates:
1. **Terraform Execution**: Provisions AWS VPC, RDS, S3, KMS, IAM, security groups
2. **Application Deployment**: Builds Docker image, deploys FastAPI container
3. **Environment Variables**: Injects Terraform outputs (RDS URL, S3 bucket) into application
4. **Health Monitoring**: Monitors application health, restarts on failures
5. **Network Configuration**: Configures VPC peering/PrivateLink for secure AWS connectivity

**Railway does NOT provision data services** - it only orchestrates Terraform and hosts application containers.

## AWS RDS pgvector Verification

### Automatic Verification (via Migration)

The application includes automatic pgvector verification in the first database migration. When Railway deploys the application, it runs `alembic upgrade head` which:

1. Connects to AWS RDS PostgreSQL (provisioned by Terraform)
2. Verifies pgvector extension is available
3. Enables the extension if not already enabled
4. Creates tables with vector columns

If pgvector is not available on the AWS RDS instance, the migration will fail with a clear error message.

**Note**: Terraform provisions RDS with `shared_preload_libraries = 'vector'` parameter to ensure pgvector is available.

### Manual Verification Steps

1. **Connect to AWS RDS PostgreSQL:**
   - Get RDS endpoint from Terraform outputs or Railway environment variables
   - Use psql client or database GUI tool to connect
   ```bash
   psql $DATABASE_URL
   ```

2. **Check extension availability:**
   ```sql
   SELECT * FROM pg_available_extensions WHERE name = 'vector';
   ```

   Expected output:
   ```
   name   | default_version | installed_version | comment
   -------|-----------------|-------------------|------------------
   vector | 0.5.1           |                   | vector data type...
   ```

3. **Verify extension is enabled:**
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```

   Expected output (after migrations run):
   ```
   extname | extversion
   --------|------------
   vector  | 0.5.1
   ```

4. **Test vector operations:**
   ```sql
   SELECT '[1,2,3]'::vector;
   SELECT '[1,2,3]'::vector <-> '[4,5,6]'::vector AS distance;
   ```

   Should return vector values without errors.

## Troubleshooting

### Issue: "pgvector extension not available"

**Symptoms:**
- Migration fails with extension error
- `pg_available_extensions` doesn't show vector extension

**Solutions:**

1. **Verify PostgreSQL image:**
   - Check Railway service uses `pgvector/pgvector:pg15` image
   - Redeploy with correct image if needed

2. **Use pgvector template:**
   - Redeploy using https://railway.com/deploy/3jJFCA
   - This ensures correct PostgreSQL image

3. **Contact Railway support:**
   - Open support ticket requesting pgvector extension
   - Provide service ID and project details

### Issue: "permission denied to create extension"

**Symptoms:**
- `CREATE EXTENSION vector` fails with permission error

**Solutions:**

1. **Verify database user permissions:**
   ```sql
   SELECT rolname, rolsuper, rolcreaterole, rolcreatedb
   FROM pg_roles
   WHERE rolname = current_user;
   ```

2. **Railway default user has superuser:**
   - Railway's `postgres` user should have superuser privileges
   - If not, contact Railway support

### Issue: Vector queries return unexpected results

**Symptoms:**
- Similarity searches don't work as expected
- Distance calculations seem incorrect

**Solutions:**

1. **Verify HNSW index exists:**
   ```sql
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename = 'documents' AND indexname LIKE '%hnsw%';
   ```

2. **Check vector dimensions:**
   ```sql
   SELECT COUNT(*), array_length(embedding_vector, 1) AS dimensions
   FROM documents
   WHERE embedding_vector IS NOT NULL
   GROUP BY dimensions;
   ```

   All embeddings should be 1024 dimensions.

3. **Rebuild HNSW index if corrupted:**
   ```sql
   REINDEX INDEX idx_documents_embedding_hnsw;
   ```

### Issue: Migration timeout during index creation

**Symptoms:**
- HNSW index creation times out
- Large documents table causes migration failure

**Solutions:**

1. **Increase statement timeout:**
   ```sql
   ALTER DATABASE railway SET statement_timeout = '30min';
   ```

2. **Create index concurrently (manual):**
   ```sql
   -- After migration creates table, manually create index:
   CREATE INDEX CONCURRENTLY idx_documents_embedding_hnsw
   ON documents
   USING hnsw (embedding_vector vector_cosine_ops)
   WHERE embedding_vector IS NOT NULL AND deleted_at IS NULL;
   ```

3. **Upgrade Railway plan:**
   - Higher-tier plans have more CPU/memory for faster indexing

## Connection Configuration

### Environment Variables (Auto-Provided by Railway)

Railway automatically injects these variables when PostgreSQL service is linked:

```bash
PGHOST=<hostname>
PGPORT=5432
PGUSER=postgres
PGPASSWORD=<generated-password>
PGDATABASE=railway
DATABASE_URL=postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE
```

### Application Connection Pooling

The backend uses SQLAlchemy async engine with connection pooling:

```python
# backend/app/database/engine.py
engine = create_async_engine(
    database_url,
    pool_size=10,        # 10 persistent connections
    max_overflow=10,     # 10 additional connections when pool full
    pool_timeout=30,     # 30s timeout for connection acquisition
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
)
```

Total connection usage: **20 connections** (pool_size + max_overflow)

### Connection Limits by Railway Plan

| Railway Plan | Max Connections | Application Fit |
|--------------|-----------------|-----------------|
| Free/Hobby   | ~20-50         | Development OK  |
| Pro          | 100+           | Production OK   |
| Enterprise   | 500+           | High-scale OK   |

**Monitoring connection usage:**
```sql
SELECT count(*) AS current_connections,
       max_connections AS max_connections
FROM pg_stat_activity, pg_settings
WHERE name = 'max_connections';
```

## Security Best Practices

### 1. Enable Encryption at Rest

**Railway PostgreSQL encryption:**
- Navigate to PostgreSQL service settings
- Enable "Encryption at Rest" (available on Pro plan)
- Restart service to apply changes

### 2. Restrict Network Access

**Railway Network Security:**
- PostgreSQL is private by default (not publicly accessible)
- Only Railway services in same project can connect
- Use Railway Private Networking for enhanced isolation

### 3. Use Strong Passwords

**Railway auto-generates strong passwords:**
- Default `POSTGRES_PASSWORD` is cryptographically random
- Never commit passwords to version control
- Rotate passwords via Railway dashboard if compromised

### 4. Enable Audit Logging

**PostgreSQL logging configuration:**
```sql
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
ALTER SYSTEM SET log_duration = 'on';
```

Then restart PostgreSQL service in Railway dashboard.

## Performance Optimization

See [POSTGRESQL_TUNING.md](POSTGRESQL_TUNING.md) for detailed performance tuning guidance.

Quick checklist:
- [ ] Adjust `shared_buffers` for available RAM
- [ ] Set `effective_cache_size` appropriately
- [ ] Configure `work_mem` for complex queries
- [ ] Enable WAL archiving for HIPAA compliance
- [ ] Set up automated backups (30+ day retention)

## Backup and Recovery

### Enable Railway Backups

1. **Enable backups:**
   - Navigate to PostgreSQL service in Railway dashboard
   - Click "Backups" tab
   - Click "Enable Backups"

2. **Configure retention:**
   - Set retention period: **30+ days** (HIPAA requirement)
   - Railway automatically snapshots database

3. **Verify backup schedule:**
   - Check "Backups" tab for completed backups
   - Verify backup size is reasonable

### Test Restoration

**Important:** Test backup restoration before production use.

1. **Create test restoration:**
   - In "Backups" tab, select recent backup
   - Click "Restore" > "New Service"
   - Railway creates new PostgreSQL service with restored data

2. **Verify data integrity:**
   - Connect to restored database
   - Run data validation queries
   - Compare row counts with production

3. **Delete test service:**
   - After validation, delete test restored service

## HIPAA Compliance Checklist

Before storing PHI (Protected Health Information):

- [ ] Business Associate Agreement (BAA) signed with Railway
- [ ] Encryption at rest enabled on PostgreSQL service
- [ ] Automated backups enabled (30+ day retention)
- [ ] Audit logging enabled (log_statement = 'all')
- [ ] Network access restricted (private networking)
- [ ] Strong passwords enforced (Railway defaults)
- [ ] PostgreSQL tuning applied (see POSTGRESQL_TUNING.md)
- [ ] Row-Level Security (RLS) policies verified (see migrations)
- [ ] Backup restoration tested successfully

## Next Steps

After PostgreSQL is set up and verified:

1. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

2. **Verify schema:**
   - Check all tables created: `tenants`, `users`, `documents`, `audit_logs`
   - Verify indexes exist
   - Confirm RLS policies enabled

3. **Seed initial data:**
   - System tenant auto-created with ID `00000000-0000-0000-0000-000000000000`
   - Create first real tenant for your organization

4. **Configure application:**
   - Set all required environment variables in Railway backend service
   - Deploy backend application
   - Verify health checks pass

## Support Resources

- **Railway Documentation:** https://docs.railway.app/databases/postgresql
- **pgvector Documentation:** https://github.com/pgvector/pgvector
- **Railway Community:** https://discord.gg/railway
- **PostgreSQL Documentation:** https://www.postgresql.org/docs/15/

For issues specific to this template, see the main repository documentation.
