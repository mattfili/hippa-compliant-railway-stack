# PostgreSQL Configuration Tuning for Railway

This guide provides production-ready PostgreSQL configuration tuning for HIPAA-compliant applications deployed on Railway.

## Overview

Railway PostgreSQL services come with default configurations suitable for general use. For production HIPAA-compliant workloads, we recommend tuning these parameters for:

- **Performance:** Optimize for RAG workload (vector similarity searches, complex queries)
- **HIPAA Compliance:** Enable WAL archiving, audit logging, connection security
- **Reliability:** Configure backups, monitoring, connection limits

## Configuration Methods

### Method 1: ALTER SYSTEM (Recommended)

Use `ALTER SYSTEM` to persist configuration changes across restarts:

```sql
-- Connect to Railway PostgreSQL console
-- Apply configuration changes
ALTER SYSTEM SET parameter_name = 'value';

-- Restart required (via Railway dashboard)
```

**Pros:**
- Changes persist across restarts
- Clean configuration management
- Easy to audit

**Cons:**
- Requires PostgreSQL restart for some parameters
- Must have superuser privileges (Railway default has this)

### Method 2: postgresql.conf (Not Available on Railway)

Railway PostgreSQL is managed, so direct `postgresql.conf` editing is not available. Use `ALTER SYSTEM` instead.

## Production Performance Optimization

### Memory Configuration

Configure based on Railway plan tier and available RAM:

#### For 8GB RAM Instance (Pro Plan Typical)

```sql
-- Shared memory for caching data
ALTER SYSTEM SET shared_buffers = '2GB';

-- Query planner's assumption of available cache
ALTER SYSTEM SET effective_cache_size = '6GB';

-- Memory for maintenance operations (VACUUM, CREATE INDEX)
ALTER SYSTEM SET maintenance_work_mem = '512MB';

-- Memory per query operation (sort, hash)
ALTER SYSTEM SET work_mem = '32MB';

-- Memory for autovacuum operations
ALTER SYSTEM SET autovacuum_work_mem = '512MB';
```

#### For 4GB RAM Instance (Starter Plan)

```sql
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET effective_cache_size = '3GB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET autovacuum_work_mem = '256MB';
```

#### For 16GB RAM Instance (Pro/Enterprise Plan)

```sql
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET autovacuum_work_mem = '1GB';
```

**Memory Tuning Guidelines:**
- `shared_buffers`: 25% of total RAM (max 8GB)
- `effective_cache_size`: 50-75% of total RAM
- `maintenance_work_mem`: 5-10% of total RAM
- `work_mem`: Start small (16-32MB), increase if needed

**Apply and restart:**
After setting memory parameters, restart PostgreSQL via Railway dashboard.

### Connection Configuration

```sql
-- Maximum concurrent connections
ALTER SYSTEM SET max_connections = '100';

-- Idle connection timeout (15 minutes)
ALTER SYSTEM SET idle_in_transaction_session_timeout = '900000';

-- Statement timeout (30 seconds for queries)
ALTER SYSTEM SET statement_timeout = '30000';

-- Lock timeout (10 seconds)
ALTER SYSTEM SET lock_timeout = '10000';
```

**Connection Limits by Railway Plan:**

| Railway Plan | Recommended max_connections |
|--------------|----------------------------|
| Hobby        | 20-50                      |
| Pro          | 100                        |
| Enterprise   | 200-500                    |

**Application connection pooling:**
- Backend uses 20 connections (pool_size=10 + max_overflow=10)
- Leave headroom for admin connections and monitoring

### Query Performance

```sql
-- Random page cost for SSD storage
ALTER SYSTEM SET random_page_cost = '1.1';

-- Sequential page cost (baseline)
ALTER SYSTEM SET seq_page_cost = '1.0';

-- CPU tuple cost
ALTER SYSTEM SET cpu_tuple_cost = '0.01';

-- Parallel query workers
ALTER SYSTEM SET max_parallel_workers_per_gather = '4';
ALTER SYSTEM SET max_parallel_workers = '8';
ALTER SYSTEM SET max_worker_processes = '8';

-- Enable JIT compilation for complex queries
ALTER SYSTEM SET jit = 'on';
ALTER SYSTEM SET jit_above_cost = '100000';
```

### Write Performance

```sql
-- WAL buffers for write-heavy workloads
ALTER SYSTEM SET wal_buffers = '16MB';

-- Checkpoint configuration for smoother writes
ALTER SYSTEM SET checkpoint_timeout = '10min';
ALTER SYSTEM SET checkpoint_completion_target = '0.9';
ALTER SYSTEM SET max_wal_size = '2GB';
ALTER SYSTEM SET min_wal_size = '1GB';

-- Background writer for dirty pages
ALTER SYSTEM SET bgwriter_delay = '200ms';
ALTER SYSTEM SET bgwriter_lru_maxpages = '100';
```

## HIPAA Compliance Settings

### Write-Ahead Logging (WAL) Configuration

Enable WAL archiving for audit trail and point-in-time recovery:

```sql
-- Enable WAL level for replication and archiving
ALTER SYSTEM SET wal_level = 'replica';

-- Enable archive mode (requires restart)
ALTER SYSTEM SET archive_mode = 'on';

-- Archive command (Railway handles this, but configure if needed)
-- ALTER SYSTEM SET archive_command = 'cp %p /var/lib/postgresql/wal_archive/%f';

-- WAL retention for recovery
ALTER SYSTEM SET wal_keep_size = '1GB';
```

**Restart required after changing WAL settings.**

### Audit Logging

Enable comprehensive logging for HIPAA audit requirements:

```sql
-- Log all DDL and DML statements
ALTER SYSTEM SET log_statement = 'all';

-- Log query duration
ALTER SYSTEM SET log_duration = 'on';
ALTER SYSTEM SET log_min_duration_statement = '0';

-- Log connections and disconnections
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';

-- Log checkpoints for recovery auditing
ALTER SYSTEM SET log_checkpoints = 'on';

-- Log lock waits longer than 1 second
ALTER SYSTEM SET log_lock_waits = 'on';
ALTER SYSTEM SET deadlock_timeout = '1s';

-- Include application name in logs
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Detailed error information
ALTER SYSTEM SET log_error_verbosity = 'default';
```

**Warning:** Full statement logging (`log_statement = 'all'`) generates large log volumes. Monitor Railway log storage usage.

### Data Encryption

**Encryption at rest:**
- Enable in Railway PostgreSQL service settings
- Available on Pro plan and above
- See [RAILWAY_SETUP.md](RAILWAY_SETUP.md) for details

**Encryption in transit:**
```sql
-- Enforce SSL/TLS connections
ALTER SYSTEM SET ssl = 'on';

-- Minimum TLS version (Railway handles this)
-- ALTER SYSTEM SET ssl_min_protocol_version = 'TLSv1.2';
```

## Vector Search Optimization (pgvector)

Optimize for RAG workload with vector similarity searches:

```sql
-- Increase shared memory for vector operations
-- (Already set in memory configuration above)

-- Configure HNSW index parameters (set during index creation)
-- See migration files for:
-- - m = 16 (bi-directional links per node)
-- - ef_construction = 64 (dynamic candidate list size)

-- Tune for vector query performance
ALTER SYSTEM SET effective_io_concurrency = '200';
```

**HNSW Index Tuning:**

If vector searches are slow, adjust index parameters by recreating index:

```sql
-- Drop existing index
DROP INDEX idx_documents_embedding_hnsw;

-- Recreate with custom parameters
CREATE INDEX idx_documents_embedding_hnsw
ON documents
USING hnsw (embedding_vector vector_cosine_ops)
WITH (m = 32, ef_construction = 128)
WHERE embedding_vector IS NOT NULL AND deleted_at IS NULL;
```

**Parameter guidelines:**
- Higher `m` (16-64): Better recall, slower inserts, larger index
- Higher `ef_construction` (64-256): Better recall, slower index build
- Start with defaults (m=16, ef=64), increase if recall is insufficient

**Query-time tuning:**

```sql
-- Set search quality (higher = better recall, slower)
SET hnsw.ef_search = 100;

-- Execute similarity search
SELECT * FROM documents
ORDER BY embedding_vector <-> '[...]'::vector
LIMIT 10;
```

## Backup Configuration

Railway handles backups, but verify configuration:

### Enable Automated Backups

1. Navigate to PostgreSQL service in Railway dashboard
2. Click "Backups" tab
3. Enable backups with these settings:
   - **Frequency:** Daily (minimum)
   - **Retention:** 30+ days (HIPAA requirement)
   - **Verify:** Check backup completion logs

### Manual Backup Testing

```bash
# Create manual backup via Railway dashboard
# Or use pg_dump for exports:

pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Test restoration:
psql $TEST_DATABASE_URL < backup_20251016_120000.sql
```

### Backup Validation

```sql
-- After restoration, verify data integrity:

-- Check row counts
SELECT 'tenants' AS table_name, COUNT(*) AS row_count FROM tenants
UNION ALL
SELECT 'users', COUNT(*) FROM users
UNION ALL
SELECT 'documents', COUNT(*) FROM documents
UNION ALL
SELECT 'audit_logs', COUNT(*) FROM audit_logs;

-- Verify latest audit log entry
SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 1;

-- Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';
```

## Monitoring and Maintenance

### Enable pg_stat_statements

Track query performance over time:

```sql
-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Configure statement tracking
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = '10000';
```

**Restart required after enabling extension.**

### Monitor Queries

```sql
-- Top 10 slowest queries
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Most frequently executed queries
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 10;
```

### Monitor Index Usage

```sql
-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;

-- Find unused indexes (candidates for removal)
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname = 'public';
```

### Monitor Table Sizes

```sql
-- Table sizes with indexes
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Vacuum and Analyze

Configure autovacuum for multi-tenant workload:

```sql
-- Autovacuum configuration
ALTER SYSTEM SET autovacuum = 'on';
ALTER SYSTEM SET autovacuum_naptime = '1min';
ALTER SYSTEM SET autovacuum_vacuum_threshold = '50';
ALTER SYSTEM SET autovacuum_analyze_threshold = '50';
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = '0.2';
ALTER SYSTEM SET autovacuum_analyze_scale_factor = '0.1';

-- More aggressive autovacuum for high-write tables
ALTER TABLE audit_logs SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);
```

## Configuration Validation

### Verify Applied Settings

```sql
-- View all custom settings
SELECT name, setting, unit, source
FROM pg_settings
WHERE source != 'default'
ORDER BY name;

-- View specific setting
SHOW shared_buffers;
SHOW effective_cache_size;
SHOW max_connections;
```

### Restart PostgreSQL

After applying `ALTER SYSTEM` changes:

1. Navigate to Railway PostgreSQL service
2. Click "Settings" tab
3. Click "Restart"
4. Wait for service to become healthy

### Test Configuration

```sql
-- Test memory allocation
EXPLAIN ANALYZE
SELECT * FROM documents
ORDER BY created_at DESC
LIMIT 100;

-- Test vector search performance
EXPLAIN ANALYZE
SELECT * FROM documents
ORDER BY embedding_vector <-> '[...]'::vector
LIMIT 10;

-- Check connection limits
SELECT count(*) AS current_connections,
       (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connections,
       (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') - count(*) AS available_connections
FROM pg_stat_activity;
```

## Performance Troubleshooting

### Issue: Slow queries

**Diagnosis:**
```sql
-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND n_distinct > 100
  AND correlation < 0.5
ORDER BY tablename, attname;

-- Check for sequential scans on large tables
SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch
FROM pg_stat_user_tables
WHERE schemaname = 'public'
  AND seq_scan > 100
ORDER BY seq_scan DESC;
```

**Solutions:**
- Add missing indexes
- Increase `work_mem` for complex queries
- Analyze query plans with `EXPLAIN ANALYZE`

### Issue: High memory usage

**Diagnosis:**
```sql
-- Check shared_buffers usage
SELECT
    count(*) AS buffers_used,
    (SELECT setting::int FROM pg_settings WHERE name = 'shared_buffers') AS total_buffers,
    round(100.0 * count(*) / (SELECT setting::int FROM pg_settings WHERE name = 'shared_buffers'), 2) AS usage_percent
FROM pg_buffercache;
```

**Solutions:**
- Reduce `shared_buffers` if over-allocated
- Reduce `work_mem` to limit per-query memory
- Optimize queries to use less memory

### Issue: Connection exhaustion

**Diagnosis:**
```sql
SELECT
    datname,
    usename,
    application_name,
    state,
    count(*)
FROM pg_stat_activity
GROUP BY datname, usename, application_name, state
ORDER BY count(*) DESC;
```

**Solutions:**
- Increase `max_connections`
- Reduce application connection pool size
- Close idle connections (reduce `idle_in_transaction_session_timeout`)

## Railway-Specific Considerations

### Resource Limits by Plan

| Plan       | vCPU | RAM  | Storage | Recommended Config |
|------------|------|------|---------|-------------------|
| Hobby      | 1    | 4GB  | 10GB    | Starter config    |
| Pro        | 2    | 8GB  | 20GB    | Production config |
| Enterprise | 4+   | 16GB+| 50GB+   | High-scale config |

### Monitoring Railway Metrics

Railway provides built-in metrics:
- CPU usage
- Memory usage
- Disk I/O
- Network traffic

Monitor these via Railway dashboard to identify performance bottlenecks.

### Scaling Considerations

**Vertical Scaling (Recommended):**
- Upgrade Railway plan for more CPU/RAM
- Reapply tuning parameters for new resource tier

**Horizontal Scaling (Future):**
- PostgreSQL read replicas (coming to Railway)
- Connection pooler (PgBouncer) for connection multiplexing

## Complete Production Configuration Script

Apply all recommended settings for 8GB RAM production instance:

```sql
-- Memory configuration
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET work_mem = '32MB';
ALTER SYSTEM SET autovacuum_work_mem = '512MB';

-- Connection configuration
ALTER SYSTEM SET max_connections = '100';
ALTER SYSTEM SET idle_in_transaction_session_timeout = '900000';
ALTER SYSTEM SET statement_timeout = '30000';
ALTER SYSTEM SET lock_timeout = '10000';

-- Query performance
ALTER SYSTEM SET random_page_cost = '1.1';
ALTER SYSTEM SET seq_page_cost = '1.0';
ALTER SYSTEM SET cpu_tuple_cost = '0.01';
ALTER SYSTEM SET max_parallel_workers_per_gather = '4';
ALTER SYSTEM SET max_parallel_workers = '8';
ALTER SYSTEM SET max_worker_processes = '8';
ALTER SYSTEM SET jit = 'on';
ALTER SYSTEM SET jit_above_cost = '100000';

-- Write performance
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET checkpoint_timeout = '10min';
ALTER SYSTEM SET checkpoint_completion_target = '0.9';
ALTER SYSTEM SET max_wal_size = '2GB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET bgwriter_delay = '200ms';
ALTER SYSTEM SET bgwriter_lru_maxpages = '100';

-- HIPAA compliance
ALTER SYSTEM SET wal_level = 'replica';
ALTER SYSTEM SET archive_mode = 'on';
ALTER SYSTEM SET wal_keep_size = '1GB';
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = 'on';
ALTER SYSTEM SET log_min_duration_statement = '0';
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
ALTER SYSTEM SET log_checkpoints = 'on';
ALTER SYSTEM SET log_lock_waits = 'on';
ALTER SYSTEM SET deadlock_timeout = '1s';
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Vector search optimization
ALTER SYSTEM SET effective_io_concurrency = '200';

-- Autovacuum configuration
ALTER SYSTEM SET autovacuum = 'on';
ALTER SYSTEM SET autovacuum_naptime = '1min';
ALTER SYSTEM SET autovacuum_vacuum_threshold = '50';
ALTER SYSTEM SET autovacuum_analyze_threshold = '50';
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = '0.2';
ALTER SYSTEM SET autovacuum_analyze_scale_factor = '0.1';

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = '10000';

-- Restart PostgreSQL via Railway dashboard for changes to take effect
```

## Next Steps

After applying tuning configuration:

1. **Restart PostgreSQL** via Railway dashboard
2. **Verify settings** with `SHOW ALL;`
3. **Run database migrations** if not already applied
4. **Monitor performance** using queries in "Monitoring and Maintenance" section
5. **Adjust as needed** based on actual workload patterns

For additional support:
- See [RAILWAY_SETUP.md](RAILWAY_SETUP.md) for Railway-specific guidance
- Consult PostgreSQL documentation: https://www.postgresql.org/docs/15/
- Review Railway documentation: https://docs.railway.app/
