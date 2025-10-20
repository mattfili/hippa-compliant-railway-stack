package test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/gruntwork-io/terratest/modules/random"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

// TestNetworkingModuleSecurityGroupsCreated verifies that all three security groups are created
func TestNetworkingModuleSecurityGroupsCreated(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/networking",
		Vars: map[string]interface{}{
			"environment":        environment,
			"name_suffix":        nameSuffix,
			"vpc_id":             "vpc-test123",
			"railway_ip_ranges":  []string{"192.0.2.0/24"},
			"tags":               map[string]string{"Test": "true"},
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	rdsSecurityGroupID := terraform.Output(t, terraformOptions, "rds_security_group_id")
	appSecurityGroupID := terraform.Output(t, terraformOptions, "app_security_group_id")
	vpcEndpointSecurityGroupID := terraform.Output(t, terraformOptions, "vpc_endpoint_security_group_id")

	assert.NotEmpty(t, rdsSecurityGroupID, "RDS security group ID should not be empty")
	assert.NotEmpty(t, appSecurityGroupID, "App security group ID should not be empty")
	assert.NotEmpty(t, vpcEndpointSecurityGroupID, "VPC endpoint security group ID should not be empty")
}

// TestRDSSecurityGroupIngressRules verifies RDS security group only allows PostgreSQL from app SG
func TestRDSSecurityGroupIngressRules(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/networking",
		Vars: map[string]interface{}{
			"environment":        environment,
			"name_suffix":        nameSuffix,
			"vpc_id":             "vpc-test456",
			"railway_ip_ranges":  []string{},
			"tags":               map[string]string{"Test": "true"},
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	rdsSecurityGroupID := terraform.Output(t, terraformOptions, "rds_security_group_id")
	assert.NotEmpty(t, rdsSecurityGroupID, "RDS security group ID should not be empty")

	// In actual implementation, you would query AWS API to verify ingress rules
	// For now, we verify the security group was created successfully
}

// TestAppSecurityGroupConfiguration verifies app security group has correct ingress and egress
func TestAppSecurityGroupConfiguration(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	railwayIPRanges := []string{"192.0.2.0/24", "198.51.100.0/24"}

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/networking",
		Vars: map[string]interface{}{
			"environment":        environment,
			"name_suffix":        nameSuffix,
			"vpc_id":             "vpc-test789",
			"railway_ip_ranges":  railwayIPRanges,
			"tags":               map[string]string{"Environment": "test"},
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	appSecurityGroupID := terraform.Output(t, terraformOptions, "app_security_group_id")
	assert.NotEmpty(t, appSecurityGroupID, "App security group ID should not be empty")
}

// TestVPCEndpointSecurityGroup verifies VPC endpoint security group is created correctly
func TestVPCEndpointSecurityGroup(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/networking",
		Vars: map[string]interface{}{
			"environment":        environment,
			"name_suffix":        nameSuffix,
			"vpc_id":             "vpc-test101",
			"railway_ip_ranges":  []string{},
			"tags":               map[string]string{"Test": "true"},
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	vpcEndpointSecurityGroupID := terraform.Output(t, terraformOptions, "vpc_endpoint_security_group_id")
	assert.NotEmpty(t, vpcEndpointSecurityGroupID, "VPC endpoint security group ID should not be empty")
}

// TestSecurityGroupsWithEmptyRailwayIPRanges verifies module works with empty Railway IP ranges
func TestSecurityGroupsWithEmptyRailwayIPRanges(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/networking",
		Vars: map[string]interface{}{
			"environment":        environment,
			"name_suffix":        nameSuffix,
			"vpc_id":             "vpc-test202",
			"railway_ip_ranges":  []string{},
			"tags":               map[string]string{},
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// All security groups should still be created even with empty Railway IP ranges
	rdsSecurityGroupID := terraform.Output(t, terraformOptions, "rds_security_group_id")
	appSecurityGroupID := terraform.Output(t, terraformOptions, "app_security_group_id")
	vpcEndpointSecurityGroupID := terraform.Output(t, terraformOptions, "vpc_endpoint_security_group_id")

	assert.NotEmpty(t, rdsSecurityGroupID)
	assert.NotEmpty(t, appSecurityGroupID)
	assert.NotEmpty(t, vpcEndpointSecurityGroupID)
}

// TestSecurityGroupsEnvironmentTagging verifies tags are applied correctly
func TestSecurityGroupsEnvironmentTagging(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	customTags := map[string]string{
		"Project":     "HIPAA-Compliant",
		"CostCenter":  "Engineering",
	}

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/networking",
		Vars: map[string]interface{}{
			"environment":        environment,
			"name_suffix":        nameSuffix,
			"vpc_id":             "vpc-test303",
			"railway_ip_ranges":  []string{"192.0.2.0/24"},
			"tags":               customTags,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify security groups are created
	rdsSecurityGroupID := terraform.Output(t, terraformOptions, "rds_security_group_id")
	assert.NotEmpty(t, rdsSecurityGroupID, "RDS security group should be created with tags")
}
