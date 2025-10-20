# Terraform Cost Optimization Strategies

Comprehensive guide for optimizing AWS infrastructure costs while maintaining HIPAA compliance and system reliability.

## Table of Contents

1. [Cost Overview](#cost-overview)
2. [S3 Cost Optimization](#s3-cost-optimization)
3. [RDS Cost Optimization](#rds-cost-optimization)
4. [Networking Cost Optimization](#networking-cost-optimization)
5. [Cost Monitoring and Alerts](#cost-monitoring-and-alerts)
6. [Environment-Specific Strategies](#environment-specific-strategies)
7. [Reserved Capacity and Savings Plans](#reserved-capacity-and-savings-plans)

## Cost Overview

### Monthly Cost Estimates by Environment

**Development Environment:**
| Service | Resource | Monthly Cost | Annual Cost |
|---------|----------|--------------|-------------|
| RDS | db.t3.medium, 20GB, Single-AZ | $50 | $600 |
| S3 | 3 buckets, Standard storage | $10 | $120 |
| NAT Gateway | 3 gateways + data transfer | $100 | $1,200 |
| VPC Endpoints | 2 interface endpoints | $15 | $180 |
| Data Transfer | Outbound to internet | $15 | $180 |
| **Total** | | **~$190** | **~$2,280** |

**Staging Environment:**
| Service | Resource | Monthly Cost | Annual Cost |
|---------|----------|--------------|-------------|
| RDS | db.t3.large, 50GB, Multi-AZ | $200 | $2,400 |
| S3 | 3 buckets, Standard + IA + Glacier | $25 | $300 |
| NAT Gateway | 3 gateways + data transfer | $100 | $1,200 |
| VPC Endpoints | 2 interface endpoints | $15 | $180 |
| Data Transfer | Outbound to internet | $25 | $300 |
| **Total** | | **~$365** | **~$4,380** |

**Production Environment (On-Demand):**
| Service | Resource | Monthly Cost | Annual Cost |
|---------|----------|--------------|-------------|
| RDS | db.r6g.xlarge, 100GB, Multi-AZ + Replica | $600 | $7,200 |
| S3 | 3 buckets, lifecycle policies active | $40 | $480 |
| NAT Gateway | 3 gateways + data transfer | $150 | $1,800 |
| VPC Endpoints | 2 interface endpoints | $15 | $180 |
| Data Transfer | Outbound to internet | $50 | $600 |
| AWS Config | Recorder + rules | $10 | $120 |
| CloudTrail | Logging + storage | $5 | $60 |
| **Total** | | **~$870** | **~$10,440** |

**Production Environment (With Reserved Instances):**
| Service | Resource | Monthly Cost | Savings |
|---------|----------|--------------|---------|
| RDS | db.r6g.xlarge (3-year RI, all upfront) | $240 | 60% |
| S3 | Same as above | $40 | N/A |
| NAT Gateway | Same as above | $150 | N/A |
| VPC Endpoints | Same as above | $15 | N/A |
| Data Transfer | Same as above | $50 | N/A |
| AWS Config | Same as above | $10 | N/A |
| CloudTrail | Same as above | $5 | N/A |
| **Total** | | **~$510** | **~$360/month** |

---

## S3 Cost Optimization

### Strategy 1: Lifecycle Policies (Already Implemented)

**Implementation:**
```hcl
# modules/s3/main.tf
resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  rule {
    id     = "transition-to-ia-and-glacier"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"  # 46% cost savings
    }

    transition {
      days          = 365
      storage_class = "GLACIER"  # 83% cost savings
    }

    expiration {
      days = 2555  # 7 years (HIPAA requirement)
    }
  }
}
```

**Cost Savings Example (1TB dataset):**
| Storage Duration | Storage Class | Monthly Cost | Annual Cost |
|------------------|---------------|--------------|-------------|
| 0-90 days | Standard | $23/month | $276 |
| 91-365 days | Standard-IA | $12.50/month | $150 |
| 365+ days | Glacier | $4/month | $48 |
| **Weighted Average** | | **~$8/month** | **~$96** |
| **Without Lifecycle** | Standard only | $23/month | $276 |
| **Savings** | | **65% reduction** | **~$180/year** |

---

### Strategy 2: S3 Intelligent-Tiering (Alternative)

**When to Use:**
- Access patterns unpredictable
- Want automatic optimization without manual lifecycle policies
- Cost: $0.0025 per 1,000 objects monitored

**Implementation:**
```hcl
# Alternative to standard lifecycle policies
resource "aws_s3_bucket_intelligent_tiering_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  name   = "EntireBucket"

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}
```

**Cost Comparison:**
- Small datasets (< 128KB objects): Lifecycle policies cheaper
- Large datasets with unpredictable access: Intelligent-Tiering cheaper
- Current implementation: Lifecycle policies optimal for document storage

---

### Strategy 3: S3 Bucket Key (Already Implemented)

**Implementation:**
```hcl
# modules/s3/main.tf
resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  rule {
    bucket_key_enabled = true  # Reduces KMS API costs by ~99%
  }
}
```

**Cost Savings:**
- Without Bucket Key: $0.03 per 10,000 requests to KMS
- With Bucket Key: $0.03 per 10,000,000 requests (1000x reduction)
- For 1M objects: Saves ~$30/month in KMS costs

---

### Strategy 4: Compress Objects Before Upload

**Implementation (Application-Level):**
```python
# backend/app/services/document_service.py
import gzip

def upload_document(file_content: bytes, tenant_id: str, document_id: str):
    # Compress before uploading to S3
    compressed_content = gzip.compress(file_content)

    s3_client.put_object(
        Bucket=config.s3_bucket_documents,
        Key=f"tenants/{tenant_id}/documents/{document_id}.gz",
        Body=compressed_content,
        ContentEncoding="gzip"
    )
```

**Cost Savings:**
- Text documents: 70-90% size reduction
- 1TB uncompressed → 200GB compressed
- Storage savings: $23/month → $4.60/month (80% reduction)

---

## RDS Cost Optimization

### Strategy 1: Right-Sizing Instance Classes

**Current Configuration:**
| Environment | Instance Class | vCPUs | RAM | Monthly Cost |
|-------------|----------------|-------|-----|--------------|
| Development | db.t3.medium | 2 | 4GB | $50 |
| Staging | db.t3.large | 2 | 8GB | $100 (Single-AZ) |
| Production | db.r6g.xlarge | 4 | 32GB | $300 (Multi-AZ) |

**Optimization Actions:**
1. **Monitor CPU and Memory Utilization:**
```bash
# Get RDS performance metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=hipaa-db-production \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average,Maximum

# Check memory usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeableMemory \
  --dimensions Name=DBInstanceIdentifier,Value=hipaa-db-production \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average,Minimum
```

2. **Right-Sizing Recommendations:**
- CPU < 40%: Consider smaller instance class
- CPU > 70%: Consider larger instance class
- Memory usage < 50%: Consider memory-optimized → general-purpose class

---

### Strategy 2: Reserved Instances (Production Only)

**3-Year Reserved Instance Pricing:**
| Payment Option | Upfront | Monthly | Total 3-Year | Savings vs. On-Demand |
|----------------|---------|---------|--------------|----------------------|
| No Upfront | $0 | $214 | $7,704 | 29% |
| Partial Upfront | $3,240 | $95 | $6,660 | 44% |
| All Upfront | $5,400 | $0 | $5,400 | 60% |

**Implementation:**
```bash
# Purchase RDS Reserved Instance (All Upfront, 3-Year)
aws rds purchase-reserved-db-instances-offering \
  --reserved-db-instances-offering-id <offering-id> \
  --db-instance-count 1 \
  --tags Key=Environment,Value=production

# Find offering ID:
aws rds describe-reserved-db-instances-offerings \
  --db-instance-class db.r6g.xlarge \
  --duration 94608000 \
  --product-description postgresql \
  --offering-type "All Upfront" \
  --multi-az
```

**ROI Analysis:**
- 3-year cost savings: $4,320
- Breakeven: ~8 months
- Recommendation: Purchase after production is stable (3-6 months)

---

### Strategy 3: Stop Non-Production Instances During Off-Hours

**Implementation (Development Only):**
```bash
# Create Lambda function to stop/start RDS instances
# Stop dev instances at 7 PM, start at 7 AM (weekdays only)

# Estimated savings:
# - 14 hours/day stopped (7 PM - 9 AM next day)
# - 48 hours/weekend stopped
# - Total: ~120 hours/week stopped (71% of time)
# - Savings: $50/month → $15/month (70% reduction)
```

**Terraform Configuration:**
```hcl
# Create EventBridge rule to stop RDS at 7 PM EST (weekdays)
resource "aws_cloudwatch_event_rule" "stop_dev_rds" {
  name                = "stop-dev-rds-nightly"
  description         = "Stop development RDS instances at 7 PM EST"
  schedule_expression = "cron(0 23 ? * MON-FRI *)"  # 7 PM EST = 23:00 UTC
}

# Lambda function to stop RDS
resource "aws_lambda_function" "stop_dev_rds" {
  # Lambda code to call aws rds stop-db-instance
}
```

**WARNING:** Only applicable to dev environment. Staging and production must run 24/7.

---

### Strategy 4: Use Read Replicas for Reporting

**Current Configuration:**
- Production has 1 read replica for high availability

**Optimization:**
- Use read replica for reporting queries to reduce load on primary
- Application configuration to route read-only queries to replica endpoint

**Cost Impact:**
- Read replica: $300/month (already provisioned)
- Savings: Prevents need for larger primary instance class
- Net savings: ~$200/month by avoiding upgrade to db.r6g.2xlarge

---

### Strategy 5: Storage Optimization

**Current Configuration:**
- gp3 storage: $0.08/GB/month
- Dev: 20GB = $1.60/month
- Staging: 50GB = $4/month
- Production: 100GB = $8/month

**Optimization Actions:**
1. **Monitor Storage Growth:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=hipaa-db-production \
  --start-time $(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Average
```

2. **Right-Size Storage:**
- Start with minimum (20GB), let RDS auto-scale
- Review quarterly and adjust allocated storage
- Delete old snapshots (>90 days) if no longer needed

---

## Networking Cost Optimization

### Strategy 1: VPC Endpoints vs. NAT Gateway

**Current Configuration:**
| Traffic Type | Route | Monthly Cost |
|--------------|-------|--------------|
| S3 traffic | Gateway VPC endpoint | $0 (free) |
| RDS traffic | Interface VPC endpoint | $7.30/month per AZ |
| Bedrock traffic | Interface VPC endpoint | $7.30/month per AZ |
| Other internet traffic | NAT Gateway | $32.85/month per AZ + $0.045/GB |

**Cost Comparison (1TB data transfer to S3):**
- **Without VPC Endpoint:** $32.85 NAT + $45 data transfer = $77.85/month
- **With VPC Endpoint:** $0 (gateway endpoint is free)
- **Savings:** $77.85/month = $934/year

**Already Optimized:** Terraform configuration includes VPC endpoints for S3 (gateway), RDS, and Bedrock (interface).

---

### Strategy 2: Consolidate NAT Gateways

**Current Configuration:**
- 3 NAT gateways (one per AZ) for high availability

**Optimization Option:**
- Single NAT gateway for dev environment (not production)
- Savings: $65.70/month (2 NAT gateways eliminated)
- Trade-off: No redundancy if NAT gateway fails

**Implementation (Dev Only):**
```hcl
# terraform.tfvars.dev
enable_nat_gateway = true
nat_gateway_count  = 1  # Single NAT instead of 3
```

**Recommendation:**
- Dev: Use 1 NAT gateway (acceptable downtime)
- Staging: Keep 3 NAT gateways (production-like)
- Production: Keep 3 NAT gateways (required for HA)

---

### Strategy 3: Minimize Data Transfer Costs

**Data Transfer Pricing:**
- Inbound: Free
- Outbound to internet: $0.09/GB (first 10TB/month)
- Between AZs: $0.01/GB per AZ
- Within same AZ: Free

**Optimization Actions:**
1. **Cache Frequently Accessed Data:**
   - Implement Redis cache for API responses
   - Reduces database queries and data transfer

2. **Compress API Responses:**
```python
# backend/app/main.py
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZIPMiddleware, minimum_size=1000)
```
   - Reduces outbound data transfer by 70-90%

3. **Use CloudFront CDN (Future Enhancement):**
   - Cache document previews/thumbnails
   - Reduces S3 data transfer costs
   - Cost: $0.085/GB vs. $0.09/GB direct (minor savings, but faster)

---

## Cost Monitoring and Alerts

### Strategy 1: AWS Cost Explorer and Budgets

**Implementation:**
```bash
# Create monthly budget with alerts
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget-production.json \
  --notifications-with-subscribers file://budget-notifications.json
```

**budget-production.json:**
```json
{
  "BudgetName": "hipaa-production-monthly",
  "BudgetLimit": {
    "Amount": "700",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST",
  "CostFilters": {
    "TagKeyValue": ["Environment$production"]
  }
}
```

**budget-notifications.json:**
```json
{
  "Notification": {
    "NotificationType": "ACTUAL",
    "ComparisonOperator": "GREATER_THAN",
    "Threshold": 80,
    "ThresholdType": "PERCENTAGE"
  },
  "Subscribers": [
    {
      "SubscriptionType": "EMAIL",
      "Address": "devops-team@organization.com"
    }
  ]
}
```

**Alerts:**
- 50% of budget: Warning notification
- 80% of budget: Critical notification
- 100% of budget: Escalation notification

---

### Strategy 2: Cost Allocation Tags

**Implementation (Already in Terraform):**
```hcl
# terraform/main.tf
locals {
  common_tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "HIPAA-Compliant-Document-Management"
    CostCenter  = "Engineering"
  }
}

# Applied to all resources
module "vpc" {
  tags = local.common_tags
}
```

**Cost Explorer Grouping:**
- Group by Environment tag: See dev/staging/production costs separately
- Group by Service: See RDS vs. S3 vs. NAT Gateway costs
- Group by Month: Track cost trends over time

---

### Strategy 3: Cost Estimation Script (Already Implemented)

**Usage:**
```bash
cd terraform
./scripts/estimate-costs.sh production
```

**Output:**
```
=== AWS Infrastructure Cost Estimation ===
Environment: production

RDS Costs:
  - Instance: db.r6g.xlarge Multi-AZ = $300/month
  - Storage: 100GB gp3 = $8/month
  - Backups: 30-day retention ~= $20/month
  - Read Replica: $300/month
  Total RDS: $628/month

S3 Costs:
  - Standard storage (0-90 days): $23/month
  - Standard-IA (90-365 days): $12.50/month
  - Glacier (365+ days): $4/month
  Total S3: $39.50/month

Networking Costs:
  - NAT Gateway: 3 x $32.85 = $98.55/month
  - Data Transfer: ~$50/month
  - VPC Endpoints: 2 x $7.30 = $14.60/month
  Total Networking: $163.15/month

Other Costs:
  - AWS Config: $10/month
  - CloudTrail: $5/month
  Total Other: $15/month

=== Total Estimated Monthly Cost: $845.65 ===

Optimization Recommendations:
  - Consider RDS Reserved Instances for 60% savings ($360/month)
  - S3 lifecycle policies already optimized (saving $180/year)
  - VPC endpoints already configured (saving $934/year)
```

---

## Environment-Specific Strategies

### Development Environment

**Optimization Priorities:**
1. **Stop during off-hours:** 70% savings on RDS
2. **Single NAT gateway:** 66% savings on NAT Gateway
3. **Minimal storage:** Start with 20GB, scale as needed

**Total Savings:** ~$120/month (63% reduction)

**Updated Dev Cost:**
- RDS (stopped 14h/day): $15/month
- S3: $10/month
- NAT Gateway (1 instead of 3): $32.85/month
- VPC Endpoints: $15/month
- **Total: ~$73/month** (vs. $190 original)

---

### Staging Environment

**Optimization Priorities:**
1. **Production-like configuration** (no aggressive cost-cutting)
2. **Reserved Instance** (1-year partial upfront for flexibility)
3. **Monitor and adjust storage** quarterly

**Total Savings:** ~$50/month (14% reduction) with RI

**Updated Staging Cost:**
- RDS (1-year RI): $150/month
- S3: $25/month
- NAT Gateway: $100/month
- VPC Endpoints: $15/month
- **Total: ~$315/month** (vs. $365 original)

---

### Production Environment

**Optimization Priorities:**
1. **Reserved Instances** (3-year all upfront): 60% savings
2. **S3 lifecycle policies** (already implemented): 65% savings
3. **VPC endpoints** (already implemented): $934/year savings
4. **Monitor and right-size** monthly

**Total Savings:** ~$360/month (41% reduction) with RI

**Updated Production Cost:**
- RDS (3-year RI all upfront): $150/month (primary) + $150/month (replica) = $300/month
- S3 (with lifecycle): $40/month
- NAT Gateway: $150/month
- VPC Endpoints: $15/month
- AWS Config: $10/month
- CloudTrail: $5/month
- **Total: ~$520/month** (vs. $870 original)

---

## Reserved Capacity and Savings Plans

### RDS Reserved Instances

**When to Purchase:**
- After 3-6 months in production (ensure stability)
- When monthly costs exceed $200/month
- When confident in instance class and size

**Purchase Process:**
```bash
# 1. Find offering
aws rds describe-reserved-db-instances-offerings \
  --db-instance-class db.r6g.xlarge \
  --duration 94608000 \
  --product-description postgresql \
  --multi-az \
  --offering-type "All Upfront"

# 2. Purchase
aws rds purchase-reserved-db-instances-offering \
  --reserved-db-instances-offering-id <offering-id> \
  --db-instance-count 1
```

**Savings Comparison:**
| Duration | Payment | Total Cost | Savings |
|----------|---------|------------|---------|
| On-Demand (3 years) | Monthly | $13,680 | 0% |
| 1-Year No Upfront | Monthly | $9,408 | 31% |
| 1-Year All Upfront | Upfront | $8,100 | 41% |
| 3-Year No Upfront | Monthly | $7,704 | 44% |
| 3-Year All Upfront | Upfront | $5,400 | 60% |

---

### AWS Savings Plans (Alternative)

**Compute Savings Plans:**
- Commit to spend $X/hour for 1 or 3 years
- Applies to EC2, Lambda, Fargate (NOT RDS)
- Not applicable to current infrastructure

**Future Consideration:**
- If migrating from Railway to EC2/ECS, consider Compute Savings Plans
- Current recommendation: Focus on RDS Reserved Instances only

---

## Summary and Action Plan

### Immediate Actions (Month 1)

1. **Enable S3 Lifecycle Policies:** Already implemented ✓
2. **Configure VPC Endpoints:** Already implemented ✓
3. **Set up Cost Budgets and Alerts:**
```bash
cd terraform
aws budgets create-budget --budget file://scripts/budget-production.json
```
4. **Review RDS Instance Sizing:** Check CloudWatch metrics

**Expected Savings:** $0 (already optimized) + monitoring setup

---

### Short-Term Actions (Months 2-3)

1. **Implement Dev RDS Stop/Start Schedule:**
```bash
cd terraform/scripts
./setup-rds-scheduler.sh dev
```
2. **Compress Application Responses:** Add gzip middleware
3. **Reduce Dev Environment to Single NAT Gateway:**
```hcl
# terraform.tfvars.dev
nat_gateway_count = 1
```

**Expected Savings:** ~$120/month from dev environment

---

### Long-Term Actions (Months 6-12)

1. **Purchase RDS Reserved Instances** (after 6 months in production)
2. **Implement CloudFront CDN** for document delivery
3. **Review and optimize storage quarterly**
4. **Consider Aurora Serverless** for variable workloads (future)

**Expected Savings:** ~$360/month from production RI

---

### Total Potential Savings

| Environment | Current Monthly Cost | Optimized Monthly Cost | Savings |
|-------------|---------------------|----------------------|---------|
| Development | $190 | $73 | $117 (62%) |
| Staging | $365 | $315 | $50 (14%) |
| Production | $870 | $520 | $350 (40%) |
| **Total** | **$1,425** | **$908** | **$517/month** |
| **Annual** | **$17,100** | **$10,896** | **$6,204/year** |

**ROI:**
- Implementation effort: 8-16 hours
- Annual savings: $6,204
- Payback: Immediate for most optimizations, 8 months for RDS RI

---

## Cost Optimization Checklist

### Monthly Review

- [ ] Review AWS Cost Explorer for unexpected charges
- [ ] Check budget alerts for threshold breaches
- [ ] Review CloudWatch metrics for right-sizing opportunities
- [ ] Verify S3 lifecycle policies are working (objects transitioning to IA/Glacier)
- [ ] Delete old RDS snapshots (> 90 days) if no longer needed

### Quarterly Review

- [ ] Run cost estimation script for all environments
- [ ] Review and adjust RDS instance classes based on utilization
- [ ] Review and adjust RDS storage based on growth trends
- [ ] Evaluate Reserved Instance purchase opportunities
- [ ] Review data transfer patterns and optimize VPC endpoints

### Annual Review

- [ ] Comprehensive cost optimization audit
- [ ] Evaluate new AWS services for cost savings
- [ ] Review Reserved Instance renewals
- [ ] Assess multi-region or cross-region opportunities
- [ ] Update cost optimization documentation
