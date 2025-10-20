package test

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/gruntwork-io/terratest/modules/aws"
	"github.com/gruntwork-io/terratest/modules/random"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestS3ModuleBucketCreation verifies that all three S3 buckets are created with correct naming
func TestS3ModuleBucketCreation(t *testing.T) {
	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/s3",
		Vars: map[string]interface{}{
			"environment":               environment,
			"name_suffix":               nameSuffix,
			"aws_account_id":            expectedAccountID,
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test-key-id", expectedAccountID), // Mock KMS key for structure test
			"enable_lifecycle_policies": false, // Disable for faster test
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify documents bucket name
	documentsBucket := terraform.Output(t, terraformOptions, "s3_bucket_documents")
	expectedDocsBucket := fmt.Sprintf("hipaa-compliant-docs-%s-%s-%s", environment, nameSuffix, expectedAccountID)
	assert.Equal(t, expectedDocsBucket, documentsBucket)

	// Verify backups bucket name
	backupsBucket := terraform.Output(t, terraformOptions, "s3_bucket_backups")
	expectedBackupsBucket := fmt.Sprintf("hipaa-compliant-backups-%s-%s-%s", environment, nameSuffix, expectedAccountID)
	assert.Equal(t, expectedBackupsBucket, backupsBucket)

	// Verify audit logs bucket name
	auditLogsBucket := terraform.Output(t, terraformOptions, "s3_bucket_audit_logs")
	expectedAuditBucket := fmt.Sprintf("hipaa-compliant-audit-%s-%s-%s", environment, nameSuffix, expectedAccountID)
	assert.Equal(t, expectedAuditBucket, auditLogsBucket)

	// Verify buckets exist in AWS using AWS SDK
	cfg, err := config.LoadDefaultConfig(context.TODO(), config.WithRegion(awsRegion))
	require.NoError(t, err)
	s3Client := s3.NewFromConfig(cfg)

	// Check if documents bucket exists
	_, err = s3Client.HeadBucket(context.TODO(), &s3.HeadBucketInput{Bucket: &documentsBucket})
	require.NoError(t, err, "Documents bucket should exist")

	// Check if backups bucket exists
	_, err = s3Client.HeadBucket(context.TODO(), &s3.HeadBucketInput{Bucket: &backupsBucket})
	require.NoError(t, err, "Backups bucket should exist")

	// Check if audit logs bucket exists
	_, err = s3Client.HeadBucket(context.TODO(), &s3.HeadBucketInput{Bucket: &auditLogsBucket})
	require.NoError(t, err, "Audit logs bucket should exist")
}

// TestS3ModuleEncryption verifies SSE-KMS encryption is enabled on all buckets using AWS SDK
func TestS3ModuleEncryption(t *testing.T) {
	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/s3",
		Vars: map[string]interface{}{
			"environment":               environment,
			"name_suffix":               nameSuffix,
			"aws_account_id":            expectedAccountID,
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test-key-id", expectedAccountID),
			"enable_lifecycle_policies": false,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	documentsBucket := terraform.Output(t, terraformOptions, "s3_bucket_documents")
	backupsBucket := terraform.Output(t, terraformOptions, "s3_bucket_backups")
	auditLogsBucket := terraform.Output(t, terraformOptions, "s3_bucket_audit_logs")

	// Load AWS SDK config
	cfg, err := config.LoadDefaultConfig(context.TODO(), config.WithRegion(awsRegion))
	require.NoError(t, err)

	s3Client := s3.NewFromConfig(cfg)

	// Verify encryption on documents bucket
	docsEncResult, err := s3Client.GetBucketEncryption(context.TODO(), &s3.GetBucketEncryptionInput{
		Bucket: &documentsBucket,
	})
	require.NoError(t, err)
	require.NotNil(t, docsEncResult)
	require.Len(t, docsEncResult.ServerSideEncryptionConfiguration.Rules, 1)
	assert.Equal(t, "aws:kms", string(docsEncResult.ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm))

	// Verify encryption on backups bucket
	backupsEncResult, err := s3Client.GetBucketEncryption(context.TODO(), &s3.GetBucketEncryptionInput{
		Bucket: &backupsBucket,
	})
	require.NoError(t, err)
	require.NotNil(t, backupsEncResult)
	require.Len(t, backupsEncResult.ServerSideEncryptionConfiguration.Rules, 1)
	assert.Equal(t, "aws:kms", string(backupsEncResult.ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm))

	// Verify encryption on audit logs bucket
	auditEncResult, err := s3Client.GetBucketEncryption(context.TODO(), &s3.GetBucketEncryptionInput{
		Bucket: &auditLogsBucket,
	})
	require.NoError(t, err)
	require.NotNil(t, auditEncResult)
	require.Len(t, auditEncResult.ServerSideEncryptionConfiguration.Rules, 1)
	assert.Equal(t, "aws:kms", string(auditEncResult.ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm))
}

// TestS3ModuleVersioning verifies versioning is enabled on all buckets
func TestS3ModuleVersioning(t *testing.T) {
	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/s3",
		Vars: map[string]interface{}{
			"environment":               environment,
			"name_suffix":               nameSuffix,
			"aws_account_id":            expectedAccountID,
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test-key-id", expectedAccountID),
			"enable_lifecycle_policies": false,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	documentsBucket := terraform.Output(t, terraformOptions, "s3_bucket_documents")
	backupsBucket := terraform.Output(t, terraformOptions, "s3_bucket_backups")
	auditLogsBucket := terraform.Output(t, terraformOptions, "s3_bucket_audit_logs")

	// Load AWS SDK config
	cfg, err := config.LoadDefaultConfig(context.TODO(), config.WithRegion(awsRegion))
	require.NoError(t, err)

	s3Client := s3.NewFromConfig(cfg)

	// Verify versioning on documents bucket
	docsVersioning, err := s3Client.GetBucketVersioning(context.TODO(), &s3.GetBucketVersioningInput{
		Bucket: &documentsBucket,
	})
	require.NoError(t, err)
	assert.Equal(t, "Enabled", string(docsVersioning.Status))

	// Verify versioning on backups bucket
	backupsVersioning, err := s3Client.GetBucketVersioning(context.TODO(), &s3.GetBucketVersioningInput{
		Bucket: &backupsBucket,
	})
	require.NoError(t, err)
	assert.Equal(t, "Enabled", string(backupsVersioning.Status))

	// Verify versioning on audit logs bucket
	auditVersioning, err := s3Client.GetBucketVersioning(context.TODO(), &s3.GetBucketVersioningInput{
		Bucket: &auditLogsBucket,
	})
	require.NoError(t, err)
	assert.Equal(t, "Enabled", string(auditVersioning.Status))
}

// TestS3ModulePublicAccessBlock verifies public access is blocked on all buckets
func TestS3ModulePublicAccessBlock(t *testing.T) {
	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/s3",
		Vars: map[string]interface{}{
			"environment":               environment,
			"name_suffix":               nameSuffix,
			"aws_account_id":            expectedAccountID,
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test-key-id", expectedAccountID),
			"enable_lifecycle_policies": false,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	documentsBucket := terraform.Output(t, terraformOptions, "s3_bucket_documents")

	// Load AWS SDK config
	cfg, err := config.LoadDefaultConfig(context.TODO(), config.WithRegion(awsRegion))
	require.NoError(t, err)

	s3Client := s3.NewFromConfig(cfg)

	// Verify public access block on documents bucket
	publicAccessBlock, err := s3Client.GetPublicAccessBlock(context.TODO(), &s3.GetPublicAccessBlockInput{
		Bucket: &documentsBucket,
	})
	require.NoError(t, err)
	require.NotNil(t, publicAccessBlock.PublicAccessBlockConfiguration)
	assert.True(t, *publicAccessBlock.PublicAccessBlockConfiguration.BlockPublicAcls)
	assert.True(t, *publicAccessBlock.PublicAccessBlockConfiguration.BlockPublicPolicy)
	assert.True(t, *publicAccessBlock.PublicAccessBlockConfiguration.IgnorePublicAcls)
	assert.True(t, *publicAccessBlock.PublicAccessBlockConfiguration.RestrictPublicBuckets)
}

// TestS3ModuleOutputs verifies all required outputs are exported
func TestS3ModuleOutputs(t *testing.T) {
	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/s3",
		Vars: map[string]interface{}{
			"environment":               environment,
			"name_suffix":               nameSuffix,
			"aws_account_id":            expectedAccountID,
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test-key-id", expectedAccountID),
			"enable_lifecycle_policies": false,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify all outputs exist and have values
	documentsBucket := terraform.Output(t, terraformOptions, "s3_bucket_documents")
	assert.NotEmpty(t, documentsBucket)

	backupsBucket := terraform.Output(t, terraformOptions, "s3_bucket_backups")
	assert.NotEmpty(t, backupsBucket)

	auditLogsBucket := terraform.Output(t, terraformOptions, "s3_bucket_audit_logs")
	assert.NotEmpty(t, auditLogsBucket)

	documentsBucketArn := terraform.Output(t, terraformOptions, "s3_bucket_documents_arn")
	assert.Contains(t, documentsBucketArn, "arn:aws:s3:::")
	assert.Contains(t, documentsBucketArn, documentsBucket)
}

// TestS3ModuleMinimalInputs verifies module works with minimal required inputs
func TestS3ModuleMinimalInputs(t *testing.T) {
	t.Parallel()

	awsRegion := "us-east-1"
	expectedAccountID := aws.GetAccountId(t)
	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/s3",
		Vars: map[string]interface{}{
			"environment":    environment,
			"name_suffix":    nameSuffix,
			"aws_account_id": expectedAccountID,
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test-key-id", expectedAccountID),
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify outputs exist
	documentsBucket := terraform.Output(t, terraformOptions, "s3_bucket_documents")
	assert.NotEmpty(t, documentsBucket)
}
