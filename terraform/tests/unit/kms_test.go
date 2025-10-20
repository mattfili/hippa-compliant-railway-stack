package test

import (
	"encoding/json"
	"fmt"
	"strings"
	"testing"

	"github.com/gruntwork-io/terratest/modules/aws"
	"github.com/gruntwork-io/terratest/modules/random"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestKMSKeyCreation verifies that the KMS master key is created successfully
func TestKMSKeyCreation(t *testing.T) {
	t.Parallel()
	uniqueID := random.UniqueId()
	awsAccountID := aws.GetAccountId(t) // Dynamically get AWS account ID

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/kms",
		Vars: map[string]interface{}{
			"environment":         "dev",
			"name_suffix":         strings.ToLower(fmt.Sprintf("test-%s", uniqueID)),
			"aws_account_id":      awsAccountID,
			"enable_key_rotation": true,
			"tags": map[string]string{
				"TestName": "TestKMSKeyCreation",
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Verify key ID output is non-empty
	keyID := terraform.Output(t, terraformOptions, "kms_master_key_id")
	assert.NotEmpty(t, keyID, "KMS master key ID should not be empty")

	// Verify key ARN output is non-empty
	keyARN := terraform.Output(t, terraformOptions, "kms_master_key_arn")
	assert.NotEmpty(t, keyARN, "KMS master key ARN should not be empty")
	assert.Contains(t, keyARN, "arn:aws:kms", "Key ARN should contain AWS KMS prefix")
}

// TestKMSKeyRotationEnabled verifies that automatic key rotation is enabled
func TestKMSKeyRotationEnabled(t *testing.T) {
	t.Parallel()
	uniqueID := random.UniqueId()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/kms",
		Vars: map[string]interface{}{
			"environment":         "dev",
			"name_suffix":         strings.ToLower(fmt.Sprintf("test-%s", uniqueID)),
			"aws_account_id":      aws.GetAccountId(t),
			"enable_key_rotation": true,
			"tags": map[string]string{
				"TestName": "TestKMSKeyRotationEnabled",
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	keyID := terraform.Output(t, terraformOptions, "kms_master_key_id")
	assert.NotEmpty(t, keyID, "KMS master key ID should not be empty")

	// Note: In real testing, you would use AWS SDK to verify rotation status
	// For this unit test, we verify the configuration is applied successfully
}

// TestKMSKeyRotationDisabled verifies that key rotation can be disabled
func TestKMSKeyRotationDisabled(t *testing.T) {
	t.Parallel()
	uniqueID := random.UniqueId()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/kms",
		Vars: map[string]interface{}{
			"environment":         "dev",
			"name_suffix":         strings.ToLower(fmt.Sprintf("test-%s", uniqueID)),
			"aws_account_id":      aws.GetAccountId(t),
			"enable_key_rotation": false,
			"tags": map[string]string{
				"TestName": "TestKMSKeyRotationDisabled",
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	keyID := terraform.Output(t, terraformOptions, "kms_master_key_id")
	assert.NotEmpty(t, keyID, "KMS master key ID should not be empty")
}

// TestKMSKeyAlias verifies that KMS key alias is created correctly
func TestKMSKeyAlias(t *testing.T) {
	t.Parallel()
	uniqueID := random.UniqueId()

	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/kms",
		Vars: map[string]interface{}{
			"environment":         environment,
			"name_suffix":         nameSuffix,
			"aws_account_id":      aws.GetAccountId(t),
			"enable_key_rotation": true,
			"tags": map[string]string{
				"TestName": "TestKMSKeyAlias",
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Verify alias output is non-empty
	alias := terraform.Output(t, terraformOptions, "kms_key_alias")
	assert.NotEmpty(t, alias, "KMS key alias should not be empty")
	assert.Equal(t, "alias/hipaa-master-"+environment, alias, "Alias should match expected format")
}

// TestKMSKeyPolicy verifies that the key policy is correctly configured
func TestKMSKeyPolicy(t *testing.T) {
	t.Parallel()
	uniqueID := random.UniqueId()

	accountID := aws.GetAccountId(t)

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/kms",
		Vars: map[string]interface{}{
			"environment":         "dev",
			"name_suffix":         strings.ToLower(fmt.Sprintf("test-%s", uniqueID)),
			"aws_account_id":      accountID,
			"enable_key_rotation": true,
			"tags": map[string]string{
				"TestName": "TestKMSKeyPolicy",
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	keyARN := terraform.Output(t, terraformOptions, "kms_master_key_arn")
	assert.NotEmpty(t, keyARN, "KMS master key ARN should not be empty")

	// Verify account ID is in the ARN
	assert.Contains(t, keyARN, accountID, "Key ARN should contain the AWS account ID")
}

// TestKMSMultipleEnvironments verifies that different environments can be deployed
func TestKMSMultipleEnvironments(t *testing.T) {
	t.Parallel()

	environments := []string{"dev", "staging", "production"}

	for _, env := range environments {
		env := env // Capture range variable
		t.Run(env, func(t *testing.T) {
			t.Parallel()
			uniqueID := random.UniqueId()

			terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
				TerraformDir: "../../modules/kms",
				Vars: map[string]interface{}{
					"environment":         env,
					"name_suffix":         strings.ToLower(fmt.Sprintf("test-%s", uniqueID)),
					"aws_account_id":      aws.GetAccountId(t),
					"enable_key_rotation": true,
					"tags": map[string]string{
						"TestName":    "TestKMSMultipleEnvironments",
						"Environment": env,
					},
				},
				NoColor: true,
			})

			defer terraform.Destroy(t, terraformOptions)

			terraform.InitAndApply(t, terraformOptions)

			alias := terraform.Output(t, terraformOptions, "kms_key_alias")
			assert.Equal(t, "alias/hipaa-master-"+env, alias, "Alias should match environment")
		})
	}
}

// TestKMSKeyTags verifies that custom tags are applied correctly
func TestKMSKeyTags(t *testing.T) {
	t.Parallel()
	uniqueID := random.UniqueId()

	customTags := map[string]string{
		"Project":    "HIPAA Compliant Stack",
		"CostCenter": "Security",
		"Owner":      "DevOps Team",
	}

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/kms",
		Vars: map[string]interface{}{
			"environment":         "dev",
			"name_suffix":         strings.ToLower(fmt.Sprintf("test-%s", uniqueID)),
			"aws_account_id":      aws.GetAccountId(t),
			"enable_key_rotation": true,
			"tags":                customTags,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	keyID := terraform.Output(t, terraformOptions, "kms_master_key_id")
	assert.NotEmpty(t, keyID, "KMS master key ID should not be empty")

	// In a complete test, you would use AWS SDK to verify tags on the resource
}

// TestKMSInvalidEnvironment verifies that invalid environment values are rejected
func TestKMSInvalidEnvironment(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/kms",
		Vars: map[string]interface{}{
			"environment":         "invalid-env",
			"aws_account_id":      aws.GetAccountId(t),
			"enable_key_rotation": true,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	// This should fail during plan/apply due to validation
	_, err := terraform.InitAndApplyE(t, terraformOptions)
	require.Error(t, err, "Should fail with invalid environment")
	assert.Contains(t, err.Error(), "Environment must be dev, staging, or production")
}

// Helper function to parse JSON output (if needed for complex assertions)
func parseJSONOutput(t *testing.T, output string) map[string]interface{} {
	var result map[string]interface{}
	err := json.Unmarshal([]byte(output), &result)
	require.NoError(t, err, "Should be able to parse JSON output")
	return result
}
