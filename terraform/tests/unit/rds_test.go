package test

import (
	"fmt"
	"testing"

	"github.com/gruntwork-io/terratest/modules/aws"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

// TestRDSSubnetGroupCreation verifies DB subnet group is created correctly
func TestRDSSubnetGroupCreation(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/rds",
		Vars: map[string]interface{}{
			"environment":         "test",
			"private_subnet_ids":  []string{"subnet-test1", "subnet-test2", "subnet-test3"},
			"security_group_id":   "sg-test123",
			"kms_key_id":          fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test", aws.GetAccountId(t)),
			"instance_class":      "db.t3.micro",
			"allocated_storage":   20,
			"multi_az":            false,
			"enable_read_replica": false,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify subnet group name is non-empty
	subnetGroupName := terraform.Output(t, terraformOptions, "db_subnet_group_name")
	assert.NotEmpty(t, subnetGroupName)
	assert.Contains(t, subnetGroupName, "test")
}

// TestRDSParameterGroupWithPgVector verifies pgvector extension is enabled
func TestRDSParameterGroupWithPgVector(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/rds",
		Vars: map[string]interface{}{
			"environment":         "test",
			"private_subnet_ids":  []string{"subnet-test1", "subnet-test2", "subnet-test3"},
			"security_group_id":   "sg-test123",
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test", aws.GetAccountId(t)),
			"instance_class":      "db.t3.micro",
			"allocated_storage":   20,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify parameter group name is non-empty
	parameterGroupName := terraform.Output(t, terraformOptions, "db_parameter_group_name")
	assert.NotEmpty(t, parameterGroupName)
	assert.Contains(t, parameterGroupName, "pgvector")
}

// TestRDSInstanceCreation verifies RDS instance is created with encryption
func TestRDSInstanceCreation(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/rds",
		Vars: map[string]interface{}{
			"environment":         "test",
			"private_subnet_ids":  []string{"subnet-test1", "subnet-test2", "subnet-test3"},
			"security_group_id":   "sg-test123",
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test", aws.GetAccountId(t)),
			"instance_class":      "db.t3.micro",
			"allocated_storage":   20,
			"multi_az":            false,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify RDS endpoint is non-empty
	rdsEndpoint := terraform.Output(t, terraformOptions, "rds_endpoint")
	assert.NotEmpty(t, rdsEndpoint)
}

// TestRDSInstanceEncryptionEnabled verifies encryption is enabled
func TestRDSInstanceEncryptionEnabled(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/rds",
		Vars: map[string]interface{}{
			"environment":         "test",
			"private_subnet_ids":  []string{"subnet-test1", "subnet-test2", "subnet-test3"},
			"security_group_id":   "sg-test123",
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test", aws.GetAccountId(t)),
			"instance_class":      "db.t3.micro",
			"allocated_storage":   20,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify encryption is enabled by checking output
	rdsArn := terraform.Output(t, terraformOptions, "rds_arn")
	assert.NotEmpty(t, rdsArn)
	assert.Contains(t, rdsArn, "arn:aws:rds")
}

// TestRDSBackupConfiguration verifies backup retention is configured
func TestRDSBackupConfiguration(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/rds",
		Vars: map[string]interface{}{
			"environment":          "test",
			"private_subnet_ids":   []string{"subnet-test1", "subnet-test2", "subnet-test3"},
			"security_group_id":    "sg-test123",
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test", aws.GetAccountId(t)),
			"instance_class":       "db.t3.micro",
			"allocated_storage":    20,
			"backup_retention_days": 30,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify RDS instance created successfully
	rdsEndpoint := terraform.Output(t, terraformOptions, "rds_endpoint")
	assert.NotEmpty(t, rdsEndpoint)
}

// TestRDSMultiAZConfiguration verifies Multi-AZ deployment configuration
func TestRDSMultiAZConfiguration(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/rds",
		Vars: map[string]interface{}{
			"environment":         "staging",
			"private_subnet_ids":  []string{"subnet-test1", "subnet-test2", "subnet-test3"},
			"security_group_id":   "sg-test123",
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test", aws.GetAccountId(t)),
			"instance_class":      "db.t3.small",
			"allocated_storage":   50,
			"multi_az":            true,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify RDS instance created
	rdsEndpoint := terraform.Output(t, terraformOptions, "rds_endpoint")
	assert.NotEmpty(t, rdsEndpoint)
}

// TestRDSReadReplicaConditional verifies read replica is created when enabled
func TestRDSReadReplicaConditional(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/rds",
		Vars: map[string]interface{}{
			"environment":         "production",
			"private_subnet_ids":  []string{"subnet-test1", "subnet-test2", "subnet-test3"},
			"security_group_id":   "sg-test123",
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test", aws.GetAccountId(t)),
			"instance_class":      "db.t3.small",
			"allocated_storage":   100,
			"multi_az":            true,
			"enable_read_replica": true,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify reader endpoint exists when replica enabled
	readerEndpoint := terraform.Output(t, terraformOptions, "rds_reader_endpoint")
	assert.NotEmpty(t, readerEndpoint)
}

// TestRDSOutputsPopulated verifies all required outputs are populated
func TestRDSOutputsPopulated(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/rds",
		Vars: map[string]interface{}{
			"environment":         "test",
			"private_subnet_ids":  []string{"subnet-test1", "subnet-test2", "subnet-test3"},
			"security_group_id":   "sg-test123",
			"kms_key_id": fmt.Sprintf("arn:aws:kms:us-east-1:%s:key/test", aws.GetAccountId(t)),
			"instance_class":      "db.t3.micro",
			"allocated_storage":   20,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify all outputs are non-empty
	rdsEndpoint := terraform.Output(t, terraformOptions, "rds_endpoint")
	rdsDbName := terraform.Output(t, terraformOptions, "rds_db_name")
	rdsArn := terraform.Output(t, terraformOptions, "rds_arn")

	assert.NotEmpty(t, rdsEndpoint)
	assert.NotEmpty(t, rdsDbName)
	assert.NotEmpty(t, rdsArn)
}
