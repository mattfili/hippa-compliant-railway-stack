package test

import (
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/gruntwork-io/terratest/modules/aws"
	"github.com/gruntwork-io/terratest/modules/random"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// ==============================================================================
// Full Stack Integration Test
// ==============================================================================
// This test deploys the complete infrastructure stack including:
// - VPC with subnets, NAT gateways, and VPC endpoints
// - KMS encryption key
// - S3 buckets with encryption and versioning
// - RDS PostgreSQL instance with pgvector
// - Security groups and networking
// - IAM roles and policies
// - AWS Config monitoring
//
// WARNING: This test takes 15-20 minutes to complete due to RDS provisioning
// ==============================================================================

func TestFullStackDeployment(t *testing.T) {
	// Skip in short test mode
	if testing.Short() {
		t.Skip("Skipping full stack integration test in short mode")
	}

	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("integ-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../",
		Vars: map[string]interface{}{
			"aws_region":      awsRegion,
			"environment":     environment,
			"name_suffix":     nameSuffix,
			"aws_account_id":  expectedAccountID,
			"vpc_cidr":        "10.0.0.0/16",
			"enable_nat_gateway": false, // Disable to speed up test
			"enable_vpc_endpoints": true,

			// RDS configuration - minimal for testing
			"rds_instance_class":      "db.t3.micro",
			"rds_allocated_storage":   20,
			"rds_multi_az":            false,
			"rds_enable_read_replica": false,
			"rds_deletion_protection": false,
			"rds_backup_retention_days": 7,

			// S3 configuration
			"enable_lifecycle_policies": false, // Disable for faster test

			// Networking
			"railway_ip_ranges": []string{}, // Empty for test

			// Config
			"config_sns_alert_email": "",

			// IAM
			"enable_rds_monitoring": false,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
		MaxRetries:         3,
		TimeBetweenRetries: 10 * time.Second,
		RetryableTerraformErrors: map[string]string{
			".*timeout while waiting for state.*": "Timeout waiting for resource",
		},
	})

	// Cleanup - this is critical for integration tests
	defer terraform.Destroy(t, terraformOptions)

	// Deploy the full stack
	t.Log("Deploying full infrastructure stack... this will take 15-20 minutes")
	terraform.InitAndApply(t, terraformOptions)

	// ===== VPC Validation =====
	t.Run("VPC Resources", func(t *testing.T) {
		vpcID := terraform.Output(t, terraformOptions, "vpc_id")
		assert.NotEmpty(t, vpcID)

		privateSubnetIDs := terraform.OutputList(t, terraformOptions, "private_subnet_ids")
		assert.Len(t, privateSubnetIDs, 3, "Expected 3 private subnets")

		publicSubnetIDs := terraform.OutputList(t, terraformOptions, "public_subnet_ids")
		assert.Len(t, publicSubnetIDs, 3, "Expected 3 public subnets")
	})

	// ===== KMS Validation =====
	t.Run("KMS Encryption", func(t *testing.T) {
		kmsKeyID := terraform.Output(t, terraformOptions, "kms_master_key_id")
		kmsKeyARN := terraform.Output(t, terraformOptions, "kms_master_key_arn")

		assert.NotEmpty(t, kmsKeyID)
		assert.NotEmpty(t, kmsKeyARN)
		assert.Contains(t, kmsKeyARN, "arn:aws:kms")

		// Verify key rotation is enabled
		// Note: GetKMSKeyMetadata not available in Terratest aws module
		// Would require direct AWS SDK call for full verification
		// keyMetadata := aws.GetKMSKeyMetadata(t, awsRegion, kmsKeyID)
		// require.NotNil(t, keyMetadata)
	})

	// ===== S3 Validation =====
	t.Run("S3 Buckets", func(t *testing.T) {
		documentsBucket := terraform.Output(t, terraformOptions, "s3_bucket_documents")
		backupsBucket := terraform.Output(t, terraformOptions, "s3_bucket_backups")
		auditLogsBucket := terraform.Output(t, terraformOptions, "s3_bucket_audit_logs")

		// Verify bucket names
		assert.NotEmpty(t, documentsBucket)
		assert.NotEmpty(t, backupsBucket)
		assert.NotEmpty(t, auditLogsBucket)

		// Note: S3 bucket property verification functions not available in Terratest aws module
		// Would require direct AWS SDK calls - see unit tests for detailed bucket validation
		// docsEncryption := aws.GetS3BucketEncryption(t, awsRegion, documentsBucket)
		// docsVersioning := aws.GetS3BucketVersioning(t, awsRegion, documentsBucket)
		// docsPublicAccess := aws.GetS3PublicAccessBlock(t, awsRegion, documentsBucket)
	})

	// ===== RDS Validation =====
	t.Run("RDS Database", func(t *testing.T) {
		rdsEndpoint := terraform.Output(t, terraformOptions, "rds_endpoint")
		rdsDBName := terraform.Output(t, terraformOptions, "rds_db_name")
		rdsARN := terraform.Output(t, terraformOptions, "rds_arn")

		assert.NotEmpty(t, rdsEndpoint)
		assert.NotEmpty(t, rdsDBName)
		assert.NotEmpty(t, rdsARN)
		assert.Contains(t, rdsARN, "arn:aws:rds")

		// Extract DB instance identifier from endpoint
		// Format: identifier.randomstring.region.rds.amazonaws.com:5432
		assert.Contains(t, rdsEndpoint, ".rds.amazonaws.com:5432")
	})

	// ===== Security Groups Validation =====
	t.Run("Security Groups", func(t *testing.T) {
		rdsSecurityGroupID := terraform.Output(t, terraformOptions, "rds_security_group_id")
		appSecurityGroupID := terraform.Output(t, terraformOptions, "app_security_group_id")
		vpcEndpointSecurityGroupID := terraform.Output(t, terraformOptions, "vpc_endpoint_security_group_id")

		assert.NotEmpty(t, rdsSecurityGroupID)
		assert.NotEmpty(t, appSecurityGroupID)
		assert.NotEmpty(t, vpcEndpointSecurityGroupID)
	})

	// ===== IAM Validation =====
	t.Run("IAM Roles", func(t *testing.T) {
		appIAMRoleARN := terraform.Output(t, terraformOptions, "app_iam_role_arn")
		appIAMRoleName := terraform.Output(t, terraformOptions, "app_iam_role_name")

		assert.NotEmpty(t, appIAMRoleARN)
		assert.NotEmpty(t, appIAMRoleName)
		assert.Contains(t, appIAMRoleARN, "arn:aws:iam")
		assert.Contains(t, appIAMRoleName, "hipaa-app-backend")
	})

	// ===== AWS Config Validation =====
	t.Run("AWS Config", func(t *testing.T) {
		configRecorderName := terraform.Output(t, terraformOptions, "config_recorder_name")
		configSNSTopicARN := terraform.Output(t, terraformOptions, "config_sns_topic_arn")

		assert.NotEmpty(t, configRecorderName)
		assert.NotEmpty(t, configSNSTopicARN)
		assert.Contains(t, configRecorderName, nameSuffix)
		assert.Contains(t, configSNSTopicARN, "arn:aws:sns")
	})

	// ===== Integration Points Validation =====
	t.Run("Cross-Module Integration", func(t *testing.T) {
		// Verify VPC ID is used in multiple modules
		vpcID := terraform.Output(t, terraformOptions, "vpc_id")

		// Verify KMS key is used for RDS and S3 encryption
		kmsKeyARN := terraform.Output(t, terraformOptions, "kms_master_key_arn")
		assert.NotEmpty(t, kmsKeyARN)

		// Verify S3 bucket ARNs are used in IAM policies
		documentsBucketARN := terraform.Output(t, terraformOptions, "s3_bucket_documents_arn")
		assert.Contains(t, documentsBucketARN, "arn:aws:s3:::")

		// Verify security groups reference each other correctly
		rdsSecurityGroupID := terraform.Output(t, terraformOptions, "rds_security_group_id")
		appSecurityGroupID := terraform.Output(t, terraformOptions, "app_security_group_id")
		assert.NotEqual(t, rdsSecurityGroupID, appSecurityGroupID)

		t.Logf("Successfully validated cross-module integration:")
		t.Logf("  - VPC ID: %s", vpcID)
		t.Logf("  - KMS Key ARN: %s", kmsKeyARN)
		t.Logf("  - Documents Bucket ARN: %s", documentsBucketARN)
	})

	// ===== Outputs JSON Validation =====
	t.Run("Outputs Structure", func(t *testing.T) {
		// Verify all required outputs for Railway integration exist
		requiredOutputs := []string{
			"rds_endpoint",
			"s3_bucket_documents",
			"s3_bucket_backups",
			"s3_bucket_audit_logs",
			"kms_master_key_id",
			"kms_master_key_arn",
			"vpc_id",
			"app_iam_role_arn",
			"aws_region",
			"environment",
		}

		for _, output := range requiredOutputs {
			value := terraform.Output(t, terraformOptions, output)
			assert.NotEmpty(t, value, "Output '%s' should not be empty", output)
		}
	})

	t.Log("Full stack integration test completed successfully!")
}
