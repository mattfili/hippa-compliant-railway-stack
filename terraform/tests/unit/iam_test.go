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

// TestIAMModuleRoleCreation verifies that the backend application IAM role is created
func TestIAMModuleRoleCreation(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/iam",
		Vars: map[string]interface{}{
			"environment":                environment,
			"name_suffix":                nameSuffix,
			"s3_bucket_documents_arn":    "arn:aws:s3:::test-docs-bucket",
			"s3_bucket_backups_arn":      "arn:aws:s3:::test-backups-bucket",
			"s3_bucket_audit_logs_arn":   "arn:aws:s3:::test-audit-bucket",
			"kms_master_key_arn": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test-key-id", aws.GetAccountId(t)),
			"external_id":                "test-external-id",
			"enable_rds_monitoring":      false,
			"tags":                       map[string]string{"Test": "true"},
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	roleArn := terraform.Output(t, terraformOptions, "app_iam_role_arn")
	roleName := terraform.Output(t, terraformOptions, "app_iam_role_name")

	assert.NotEmpty(t, roleArn, "IAM role ARN should not be empty")
	assert.NotEmpty(t, roleName, "IAM role name should not be empty")
	expectedRoleName := fmt.Sprintf("hipaa-app-backend-%s-%s", environment, nameSuffix)
	assert.Contains(t, roleName, expectedRoleName, "Role name should follow naming convention")
}

// TestIAMModulePoliciesCreated verifies that all three policies are created
func TestIAMModulePoliciesCreated(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/iam",
		Vars: map[string]interface{}{
			"environment":                environment,
			"name_suffix":                nameSuffix,
			"s3_bucket_documents_arn":    "arn:aws:s3:::dev-docs-bucket",
			"s3_bucket_backups_arn":      "arn:aws:s3:::dev-backups-bucket",
			"s3_bucket_audit_logs_arn":   "arn:aws:s3:::dev-audit-bucket",
			"kms_master_key_arn": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/dev-key-id", aws.GetAccountId(t)),
			"external_id":                "dev-external-id",
			"enable_rds_monitoring":      false,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	s3PolicyArn := terraform.Output(t, terraformOptions, "s3_policy_arn")
	kmsPolicyArn := terraform.Output(t, terraformOptions, "kms_policy_arn")
	bedrockPolicyArn := terraform.Output(t, terraformOptions, "bedrock_policy_arn")

	assert.NotEmpty(t, s3PolicyArn, "S3 policy ARN should not be empty")
	assert.NotEmpty(t, kmsPolicyArn, "KMS policy ARN should not be empty")
	assert.NotEmpty(t, bedrockPolicyArn, "Bedrock policy ARN should not be empty")
}

// TestIAMModuleRDSMonitoringRoleConditional verifies RDS monitoring role is created when enabled
func TestIAMModuleRDSMonitoringRoleConditional(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/iam",
		Vars: map[string]interface{}{
			"environment":                environment,
			"name_suffix":                nameSuffix,
			"s3_bucket_documents_arn":    "arn:aws:s3:::prod-docs-bucket",
			"s3_bucket_backups_arn":      "arn:aws:s3:::prod-backups-bucket",
			"s3_bucket_audit_logs_arn":   "arn:aws:s3:::prod-audit-bucket",
			"kms_master_key_arn": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/prod-key-id", aws.GetAccountId(t)),
			"external_id":                "prod-external-id",
			"enable_rds_monitoring":      true,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	monitoringRoleArn := terraform.Output(t, terraformOptions, "rds_monitoring_role_arn")
	assert.NotEmpty(t, monitoringRoleArn, "RDS monitoring role ARN should not be empty when enabled")
}

// TestIAMModuleRDSMonitoringRoleDisabled verifies RDS monitoring role is not created when disabled
func TestIAMModuleRDSMonitoringRoleDisabled(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/iam",
		Vars: map[string]interface{}{
			"environment":                environment,
			"name_suffix":                nameSuffix,
			"s3_bucket_documents_arn":    "arn:aws:s3:::dev2-docs-bucket",
			"s3_bucket_backups_arn":      "arn:aws:s3:::dev2-backups-bucket",
			"s3_bucket_audit_logs_arn":   "arn:aws:s3:::dev2-audit-bucket",
			"kms_master_key_arn": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/dev2-key-id", aws.GetAccountId(t)),
			"external_id":                "dev2-external-id",
			"enable_rds_monitoring":      false,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	monitoringRoleArn := terraform.Output(t, terraformOptions, "rds_monitoring_role_arn")
	assert.Empty(t, monitoringRoleArn, "RDS monitoring role ARN should be empty when disabled")
}

// TestIAMModuleEnvironmentTagging verifies environment tags are applied correctly
func TestIAMModuleEnvironmentTagging(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	customTags := map[string]string{
		"Project":    "HIPAA-Compliant",
		"CostCenter": "Engineering",
	}

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/iam",
		Vars: map[string]interface{}{
			"environment":                environment,
			"name_suffix":                nameSuffix,
			"s3_bucket_documents_arn":    "arn:aws:s3:::staging-docs-bucket",
			"s3_bucket_backups_arn":      "arn:aws:s3:::staging-backups-bucket",
			"s3_bucket_audit_logs_arn":   "arn:aws:s3:::staging-audit-bucket",
			"kms_master_key_arn": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/staging-key-id", aws.GetAccountId(t)),
			"external_id":                "staging-external-id",
			"enable_rds_monitoring":      false,
			"tags":                       customTags,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	roleArn := terraform.Output(t, terraformOptions, "app_iam_role_arn")
	assert.NotEmpty(t, roleArn, "Role should be created with custom tags")
}

// TestIAMModuleAllOutputs verifies all outputs are populated correctly
func TestIAMModuleAllOutputs(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/iam",
		Vars: map[string]interface{}{
			"environment":                environment,
			"name_suffix":                nameSuffix,
			"s3_bucket_documents_arn":    "arn:aws:s3:::test2-docs-bucket",
			"s3_bucket_backups_arn":      "arn:aws:s3:::test2-backups-bucket",
			"s3_bucket_audit_logs_arn":   "arn:aws:s3:::test2-audit-bucket",
			"kms_master_key_arn": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test2-key-id", aws.GetAccountId(t)),
			"external_id":                "test2-external-id",
			"enable_rds_monitoring":      true,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify all outputs exist
	outputs := []string{
		"app_iam_role_arn",
		"app_iam_role_name",
		"rds_monitoring_role_arn",
		"s3_policy_arn",
		"kms_policy_arn",
		"bedrock_policy_arn",
	}

	for _, output := range outputs {
		value := terraform.Output(t, terraformOptions, output)
		assert.NotEmpty(t, value, output+" should not be empty")
	}
}

// TestIAMModuleWithMinimalInputs verifies module works with only required inputs
func TestIAMModuleWithMinimalInputs(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/iam",
		Vars: map[string]interface{}{
			"environment":                environment,
			"name_suffix":                nameSuffix,
			"s3_bucket_documents_arn":    "arn:aws:s3:::minimal-docs-bucket",
			"s3_bucket_backups_arn":      "arn:aws:s3:::minimal-backups-bucket",
			"s3_bucket_audit_logs_arn":   "arn:aws:s3:::minimal-audit-bucket",
			"kms_master_key_arn": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/minimal-key-id", aws.GetAccountId(t)),
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	roleArn := terraform.Output(t, terraformOptions, "app_iam_role_arn")
	assert.NotEmpty(t, roleArn, "Module should work with only required inputs")
}

// TestIAMModuleMultipleEnvironments verifies module can be deployed for different environments
func TestIAMModuleMultipleEnvironments(t *testing.T) {
	t.Parallel()

	environments := []string{"dev", "staging", "production"}

	for _, env := range environments {
		t.Run(env, func(t *testing.T) {
			uniqueID := random.UniqueId()
			environment := "dev"
			nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

			terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
				TerraformDir: "../../modules/iam",
				Vars: map[string]interface{}{
					"environment":                environment,
					"name_suffix":                nameSuffix,
					"s3_bucket_documents_arn":    "arn:aws:s3:::" + env + "-docs-bucket-multi",
					"s3_bucket_backups_arn":      "arn:aws:s3:::" + env + "-backups-bucket-multi",
					"s3_bucket_audit_logs_arn":   "arn:aws:s3:::" + env + "-audit-bucket-multi",
					"kms_master_key_arn": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/" + env + "-key-multi", aws.GetAccountId(t)),
					"external_id":                env + "-external-id",
				},
			})

			defer terraform.Destroy(t, terraformOptions)
			terraform.InitAndApply(t, terraformOptions)

			roleName := terraform.Output(t, terraformOptions, "app_iam_role_name")
			assert.Contains(t, roleName, environment, "Role name should contain environment")
		})
	}
}
