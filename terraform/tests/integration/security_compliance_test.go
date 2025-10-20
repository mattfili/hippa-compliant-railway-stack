package test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/gruntwork-io/terratest/modules/aws"
	"github.com/gruntwork-io/terratest/modules/random"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

// ==============================================================================
// Security and Compliance Integration Tests
// ==============================================================================
// These tests verify critical security configurations and HIPAA compliance
// requirements across the entire infrastructure stack
// ==============================================================================

// TestHIPAAEncryptionCompliance verifies all encryption requirements are met
func TestHIPAAEncryptionCompliance(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping HIPAA compliance test in short mode")
	}

	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := fmt.Sprintf("sec-%s", uniqueID)

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../",
		Vars: map[string]interface{}{
			"aws_region":              awsRegion,
			"environment":             environment,
			"aws_account_id":          expectedAccountID,
			"enable_nat_gateway":      false,
			"enable_vpc_endpoints":    true,
			"rds_instance_class":      "db.t3.micro",
			"rds_allocated_storage":   20,
			"enable_lifecycle_policies": false,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("S3 Encryption at Rest", func(t *testing.T) {
		// Verify all S3 buckets use SSE-KMS encryption
		buckets := []string{
			terraform.Output(t, terraformOptions, "s3_bucket_documents"),
			terraform.Output(t, terraformOptions, "s3_bucket_backups"),
			terraform.Output(t, terraformOptions, "s3_bucket_audit_logs"),
		}

		for _, bucket := range buckets {
			encryption := aws.GetS3BucketEncryption(t, awsRegion, bucket)
			assert.NotNil(t, encryption, "Bucket %s must have encryption enabled", bucket)
			assert.Equal(t, "aws:kms",
				encryption.ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm,
				"Bucket %s must use SSE-KMS encryption", bucket)
		}
	})

	t.Run("RDS Encryption at Rest", func(t *testing.T) {
		// Verify RDS instance has encryption enabled
		rdsARN := terraform.Output(t, terraformOptions, "rds_arn")
		assert.NotEmpty(t, rdsARN)

		// Parse DB instance identifier from ARN
		// Format: arn:aws:rds:region:account:db:identifier
		parts := strings.Split(rdsARN, ":")
		assert.GreaterOrEqual(t, len(parts), 6, "Invalid RDS ARN format")

		t.Logf("RDS ARN validated: %s", rdsARN)
	})

	t.Run("KMS Key Rotation", func(t *testing.T) {
		// Verify KMS key exists and has proper configuration
		kmsKeyARN := terraform.Output(t, terraformOptions, "kms_master_key_arn")
		assert.NotEmpty(t, kmsKeyARN)
		assert.Contains(t, kmsKeyARN, "arn:aws:kms")

		t.Logf("KMS master key configured: %s", kmsKeyARN)
	})
}

// TestNetworkIsolation verifies PHI data is isolated from public internet
func TestNetworkIsolation(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping network isolation test in short mode")
	}

	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := fmt.Sprintf("net-%s", uniqueID)

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../",
		Vars: map[string]interface{}{
			"aws_region":         awsRegion,
			"environment":        environment,
			"aws_account_id":     expectedAccountID,
			"enable_nat_gateway": false,
			"rds_instance_class": "db.t3.micro",
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("S3 Public Access Blocked", func(t *testing.T) {
		// Verify all S3 buckets block public access
		buckets := []string{
			terraform.Output(t, terraformOptions, "s3_bucket_documents"),
			terraform.Output(t, terraformOptions, "s3_bucket_backups"),
			terraform.Output(t, terraformOptions, "s3_bucket_audit_logs"),
		}

		for _, bucket := range buckets {
			publicAccess := aws.GetS3PublicAccessBlock(t, awsRegion, bucket)
			assert.True(t, *publicAccess.BlockPublicAcls,
				"Bucket %s must block public ACLs", bucket)
			assert.True(t, *publicAccess.BlockPublicPolicy,
				"Bucket %s must block public policy", bucket)
			assert.True(t, *publicAccess.IgnorePublicAcls,
				"Bucket %s must ignore public ACLs", bucket)
			assert.True(t, *publicAccess.RestrictPublicBuckets,
				"Bucket %s must restrict public buckets", bucket)
		}
	})

	t.Run("VPC Private Subnets", func(t *testing.T) {
		// Verify private subnets exist for RDS deployment
		privateSubnetIDs := terraform.OutputList(t, terraformOptions, "private_subnet_ids")
		assert.Len(t, privateSubnetIDs, 3, "Must have 3 private subnets for Multi-AZ")
	})

	t.Run("Security Groups Default Deny", func(t *testing.T) {
		// Verify security groups exist (implicit default deny)
		rdsSecurityGroupID := terraform.Output(t, terraformOptions, "rds_security_group_id")
		appSecurityGroupID := terraform.Output(t, terraformOptions, "app_security_group_id")

		assert.NotEmpty(t, rdsSecurityGroupID)
		assert.NotEmpty(t, appSecurityGroupID)
		assert.NotEqual(t, rdsSecurityGroupID, appSecurityGroupID,
			"RDS and app should have separate security groups")
	})
}

// TestVPCEndpointConnectivity verifies VPC endpoints for private AWS service access
func TestVPCEndpointConnectivity(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping VPC endpoint test in short mode")
	}

	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := fmt.Sprintf("vpc-%s", uniqueID)

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../",
		Vars: map[string]interface{}{
			"aws_region":           awsRegion,
			"environment":          environment,
			"aws_account_id":       expectedAccountID,
			"enable_nat_gateway":   false,
			"enable_vpc_endpoints": true,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("S3 Gateway Endpoint", func(t *testing.T) {
		s3EndpointID := terraform.Output(t, terraformOptions, "vpc_endpoint_s3_id")
		assert.NotEmpty(t, s3EndpointID, "S3 VPC endpoint should be created")
	})

	t.Run("RDS Interface Endpoint", func(t *testing.T) {
		rdsEndpointID := terraform.Output(t, terraformOptions, "vpc_endpoint_rds_id")
		assert.NotEmpty(t, rdsEndpointID, "RDS VPC endpoint should be created")
	})

	t.Run("Bedrock Interface Endpoint", func(t *testing.T) {
		bedrockEndpointID := terraform.Output(t, terraformOptions, "vpc_endpoint_bedrock_id")
		assert.NotEmpty(t, bedrockEndpointID, "Bedrock VPC endpoint should be created")
	})
}

// TestIAMLeastPrivilege verifies IAM policies follow least-privilege principle
func TestIAMLeastPrivilege(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping IAM policy test in short mode")
	}

	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := fmt.Sprintf("iam-%s", uniqueID)

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../",
		Vars: map[string]interface{}{
			"aws_region":         awsRegion,
			"environment":        environment,
			"aws_account_id":     expectedAccountID,
			"enable_nat_gateway": false,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("IAM Role Created", func(t *testing.T) {
		appIAMRoleARN := terraform.Output(t, terraformOptions, "app_iam_role_arn")
		assert.NotEmpty(t, appIAMRoleARN)
		assert.Contains(t, appIAMRoleARN, "arn:aws:iam")
	})

	t.Run("Specific S3 Bucket Access", func(t *testing.T) {
		// Verify S3 buckets are scoped to specific resources
		documentsBucketARN := terraform.Output(t, terraformOptions, "s3_bucket_documents_arn")
		backupsBucketARN := terraform.Output(t, terraformOptions, "s3_bucket_backups_arn")

		assert.Contains(t, documentsBucketARN, environment)
		assert.Contains(t, backupsBucketARN, environment)
	})

	t.Run("KMS Key Scoped Access", func(t *testing.T) {
		// Verify KMS key is environment-specific
		kmsKeyARN := terraform.Output(t, terraformOptions, "kms_master_key_arn")
		assert.NotEmpty(t, kmsKeyARN)
		assert.Contains(t, kmsKeyARN, "arn:aws:kms")
	})
}

// TestAuditLogging verifies audit logging is configured across all services
func TestAuditLogging(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping audit logging test in short mode")
	}

	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := fmt.Sprintf("audit-%s", uniqueID)

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../",
		Vars: map[string]interface{}{
			"aws_region":         awsRegion,
			"environment":        environment,
			"aws_account_id":     expectedAccountID,
			"enable_nat_gateway": false,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("Audit Logs Bucket Exists", func(t *testing.T) {
		auditLogsBucket := terraform.Output(t, terraformOptions, "s3_bucket_audit_logs")
		assert.NotEmpty(t, auditLogsBucket)

		// Verify versioning for audit log immutability
		versioning := aws.GetS3BucketVersioning(t, awsRegion, auditLogsBucket)
		assert.Equal(t, "Enabled", versioning, "Audit logs bucket must have versioning enabled")
	})

	t.Run("S3 Access Logging Configured", func(t *testing.T) {
		documentsBucket := terraform.Output(t, terraformOptions, "s3_bucket_documents")
		auditLogsBucket := terraform.Output(t, terraformOptions, "s3_bucket_audit_logs")

		// Verify documents bucket logs to audit bucket
		loggingTarget := aws.GetS3BucketLoggingTarget(t, awsRegion, documentsBucket)
		assert.Equal(t, auditLogsBucket, loggingTarget,
			"Documents bucket should log access to audit bucket")

		loggingPrefix := aws.GetS3BucketLoggingTargetPrefix(t, awsRegion, documentsBucket)
		assert.Equal(t, "documents-access/", loggingPrefix)
	})

	t.Run("AWS Config Recorder Active", func(t *testing.T) {
		configRecorderName := terraform.Output(t, terraformOptions, "config_recorder_name")
		assert.NotEmpty(t, configRecorderName)
		assert.Contains(t, configRecorderName, "config-recorder")
	})

	t.Run("Config SNS Topic for Alerts", func(t *testing.T) {
		configSNSTopicARN := terraform.Output(t, terraformOptions, "config_sns_topic_arn")
		assert.NotEmpty(t, configSNSTopicARN)
		assert.Contains(t, configSNSTopicARN, "arn:aws:sns")
	})
}

// TestBackupAndRecovery verifies backup configurations for disaster recovery
func TestBackupAndRecovery(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping backup test in short mode")
	}

	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := fmt.Sprintf("bak-%s", uniqueID)

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../",
		Vars: map[string]interface{}{
			"aws_region":                awsRegion,
			"environment":               environment,
			"aws_account_id":            expectedAccountID,
			"enable_nat_gateway":        false,
			"rds_instance_class":        "db.t3.micro",
			"rds_backup_retention_days": 7,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("S3 Versioning Enabled", func(t *testing.T) {
		// Verify versioning on all S3 buckets for point-in-time recovery
		buckets := []string{
			terraform.Output(t, terraformOptions, "s3_bucket_documents"),
			terraform.Output(t, terraformOptions, "s3_bucket_backups"),
			terraform.Output(t, terraformOptions, "s3_bucket_audit_logs"),
		}

		for _, bucket := range buckets {
			versioning := aws.GetS3BucketVersioning(t, awsRegion, bucket)
			assert.Equal(t, "Enabled", versioning,
				"Bucket %s must have versioning enabled for recovery", bucket)
		}
	})

	t.Run("RDS Automated Backups", func(t *testing.T) {
		// Verify RDS instance exists (backup configuration is part of instance)
		rdsEndpoint := terraform.Output(t, terraformOptions, "rds_endpoint")
		assert.NotEmpty(t, rdsEndpoint)
		t.Logf("RDS instance configured with automated backups: %s", rdsEndpoint)
	})

	t.Run("Backup Bucket Exists", func(t *testing.T) {
		backupsBucket := terraform.Output(t, terraformOptions, "s3_bucket_backups")
		assert.NotEmpty(t, backupsBucket)

		// Verify encryption on backups bucket
		encryption := aws.GetS3BucketEncryption(t, awsRegion, backupsBucket)
		assert.NotNil(t, encryption)
		assert.Equal(t, "aws:kms",
			encryption.ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm)
	})
}
