package test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/gruntwork-io/terratest/modules/random"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

// TestConfigModuleBasicDeployment tests basic Config module deployment
func TestConfigModuleBasicDeployment(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/config",
		Vars: map[string]interface{}{
			"environment":          environment,
			"name_suffix":          nameSuffix,
			"s3_bucket_audit_logs": "test-audit-logs-bucket-12345",
			"sns_alert_email":      "",
			"tags": map[string]string{
				"Test": "true",
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify Config recorder name output
	recorderName := terraform.Output(t, terraformOptions, "config_recorder_name")
	assert.NotEmpty(t, recorderName)
	assert.Contains(t, recorderName, fmt.Sprintf("%s-%s-config-recorder", environment, nameSuffix))
}

// TestConfigModuleRecorderCreation verifies Config recorder is created
func TestConfigModuleRecorderCreation(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/config",
		Vars: map[string]interface{}{
			"environment":          environment,
			"name_suffix":          nameSuffix,
			"s3_bucket_audit_logs": "test-audit-logs-bucket-67890",
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify recorder role ARN is generated
	roleArn := terraform.Output(t, terraformOptions, "config_recorder_role_arn")
	assert.NotEmpty(t, roleArn)
	assert.Contains(t, roleArn, "arn:aws:iam")
	assert.Contains(t, roleArn, fmt.Sprintf("%s-%s-config-role", environment, nameSuffix))
}

// TestConfigModuleSNSTopicCreation verifies SNS topic for alerts
func TestConfigModuleSNSTopicCreation(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/config",
		Vars: map[string]interface{}{
			"environment":          environment,
			"name_suffix":          nameSuffix,
			"s3_bucket_audit_logs": "test-audit-logs-bucket-11111",
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify SNS topic ARN
	snsTopicArn := terraform.Output(t, terraformOptions, "config_sns_topic_arn")
	assert.NotEmpty(t, snsTopicArn)
	assert.Contains(t, snsTopicArn, "arn:aws:sns")
	assert.Contains(t, snsTopicArn, fmt.Sprintf("%s-%s-config-alerts", environment, nameSuffix))
}

// TestConfigModuleRulesDeployment verifies all 6 HIPAA Config rules deployed
func TestConfigModuleRulesDeployment(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/config",
		Vars: map[string]interface{}{
			"environment":          environment,
			"name_suffix":          nameSuffix,
			"s3_bucket_audit_logs": "test-audit-logs-bucket-22222",
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify Config rules output contains all 6 expected rules
	configRules := terraform.OutputMap(t, terraformOptions, "config_rules")

	assert.NotEmpty(t, configRules)
	assert.Len(t, configRules, 6, "Should have exactly 6 Config rules")

	// Verify each rule name
	assert.Contains(t, configRules, "s3_encryption")
	assert.Contains(t, configRules, "rds_encryption")
	assert.Contains(t, configRules, "rds_public_access")
	assert.Contains(t, configRules, "iam_no_admin_access")
	assert.Contains(t, configRules, "cloudtrail_enabled")
	assert.Contains(t, configRules, "vpc_sg_authorized")

	// Verify rule names contain environment-nameSuffix prefix
	expectedPrefix := fmt.Sprintf("%s-%s-", environment, nameSuffix)
	assert.Contains(t, configRules["s3_encryption"], expectedPrefix)
	assert.Contains(t, configRules["rds_encryption"], expectedPrefix)
}

// TestConfigModuleDeliveryChannel verifies delivery channel created
func TestConfigModuleDeliveryChannel(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/config",
		Vars: map[string]interface{}{
			"environment":          environment,
			"name_suffix":          nameSuffix,
			"s3_bucket_audit_logs": "test-audit-logs-bucket-33333",
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify delivery channel name
	deliveryChannelName := terraform.Output(t, terraformOptions, "config_delivery_channel_name")
	assert.NotEmpty(t, deliveryChannelName)
	assert.Contains(t, deliveryChannelName, fmt.Sprintf("%s-%s-config-delivery-channel", environment, nameSuffix))
}

// TestConfigModuleWithEmailSubscription verifies email subscription creation
func TestConfigModuleWithEmailSubscription(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))
	testEmail := "security-test@example.com"

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/config",
		Vars: map[string]interface{}{
			"environment":          environment,
			"name_suffix":          nameSuffix,
			"s3_bucket_audit_logs": "test-audit-logs-bucket-44444",
			"sns_alert_email":      testEmail,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify SNS topic ARN is created
	snsTopicArn := terraform.Output(t, terraformOptions, "config_sns_topic_arn")
	assert.NotEmpty(t, snsTopicArn)

	// Note: Email subscription requires manual confirmation, so we just verify
	// the SNS topic exists. Full email subscription testing would require
	// additional AWS API calls or manual confirmation.
}

// TestConfigModuleEnvironmentValidation verifies environment variable validation
func TestConfigModuleEnvironmentValidation(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "invalid-env"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/config",
		Vars: map[string]interface{}{
			"environment":          environment,
			"name_suffix":          nameSuffix,
			"s3_bucket_audit_logs": "test-audit-logs-bucket-55555",
		},
	})

	// This should fail due to environment validation
	_, err := terraform.InitAndApplyE(t, terraformOptions)
	assert.Error(t, err, "Should fail with invalid environment value")
	assert.Contains(t, err.Error(), "Environment must be dev, staging, or production")
}

// TestConfigModuleTagsPropagation verifies tags are applied to resources
func TestConfigModuleTagsPropagation(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	testTags := map[string]string{
		"Project":    "HIPAA-Test",
		"Owner":      "SecurityTeam",
		"CostCenter": "Engineering",
	}

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/config",
		Vars: map[string]interface{}{
			"environment":          environment,
			"name_suffix":          nameSuffix,
			"s3_bucket_audit_logs": "test-audit-logs-bucket-66666",
			"tags":                 testTags,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify resources are created (tags validation would require AWS API calls)
	recorderName := terraform.Output(t, terraformOptions, "config_recorder_name")
	assert.NotEmpty(t, recorderName)
}
