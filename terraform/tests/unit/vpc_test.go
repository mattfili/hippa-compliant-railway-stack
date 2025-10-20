package test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/gruntwork-io/terratest/modules/random"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

// ==============================================================================
// VPC Module Tests
// ==============================================================================
// These tests verify the VPC module creates expected networking resources
// including VPC, subnets, gateways, and VPC endpoints
// ==============================================================================

// TestVPCCreation verifies that the VPC is created with correct configuration
func TestVPCCreation(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/vpc",
		Vars: map[string]interface{}{
			"vpc_cidr":            "10.0.0.0/16",
			"environment":         environment,
			"name_suffix":         nameSuffix,
			"availability_zones":  []string{"us-east-1a", "us-east-1b", "us-east-1c"},
			"enable_nat_gateway":  false, // Disable to speed up tests
			"enable_vpc_endpoints": false, // Disable to speed up tests
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Verify VPC ID is not empty
	vpcID := terraform.Output(t, terraformOptions, "vpc_id")
	assert.NotEmpty(t, vpcID)

	// Verify VPC CIDR block
	vpcCIDR := terraform.Output(t, terraformOptions, "vpc_cidr_block")
	assert.Equal(t, "10.0.0.0/16", vpcCIDR)
}

// TestSubnetCreation verifies public and private subnets are created across AZs
func TestSubnetCreation(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/vpc",
		Vars: map[string]interface{}{
			"vpc_cidr":            "10.0.0.0/16",
			"environment":         environment,
			"name_suffix":         nameSuffix,
			"availability_zones":  []string{"us-east-1a", "us-east-1b", "us-east-1c"},
			"enable_nat_gateway":  false,
			"enable_vpc_endpoints": false,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Verify private subnets
	privateSubnets := terraform.OutputList(t, terraformOptions, "private_subnet_ids")
	assert.Len(t, privateSubnets, 3, "Expected 3 private subnets")

	// Verify public subnets
	publicSubnets := terraform.OutputList(t, terraformOptions, "public_subnet_ids")
	assert.Len(t, publicSubnets, 3, "Expected 3 public subnets")
}

// TestInternetGateway verifies Internet Gateway is created
func TestInternetGateway(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/vpc",
		Vars: map[string]interface{}{
			"vpc_cidr":            "10.0.0.0/16",
			"environment":         environment,
			"name_suffix":         nameSuffix,
			"enable_nat_gateway":  false,
			"enable_vpc_endpoints": false,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Verify Internet Gateway ID is not empty
	igwID := terraform.Output(t, terraformOptions, "internet_gateway_id")
	assert.NotEmpty(t, igwID)
}

// TestNATGatewayCreation verifies NAT Gateways are created when enabled
func TestNATGatewayCreation(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/vpc",
		Vars: map[string]interface{}{
			"vpc_cidr":            "10.0.0.0/16",
			"environment":         environment,
			"name_suffix":         nameSuffix,
			"enable_nat_gateway":  true, // Enable NAT gateways
			"enable_vpc_endpoints": false,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Verify NAT Gateway IDs
	natGatewayIDs := terraform.OutputList(t, terraformOptions, "nat_gateway_ids")
	assert.Len(t, natGatewayIDs, 3, "Expected 3 NAT gateways (one per AZ)")
}

// TestNATGatewayDisabled verifies NAT Gateways are not created when disabled
func TestNATGatewayDisabled(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/vpc",
		Vars: map[string]interface{}{
			"vpc_cidr":            "10.0.0.0/16",
			"environment":         environment,
			"name_suffix":         nameSuffix,
			"enable_nat_gateway":  false, // Disable NAT gateways
			"enable_vpc_endpoints": false,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Verify NAT Gateway IDs list is empty
	natGatewayIDs := terraform.OutputList(t, terraformOptions, "nat_gateway_ids")
	assert.Empty(t, natGatewayIDs, "Expected no NAT gateways when disabled")
}

// TestRouteTables verifies route tables are created
func TestRouteTables(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/vpc",
		Vars: map[string]interface{}{
			"vpc_cidr":            "10.0.0.0/16",
			"environment":         environment,
			"name_suffix":         nameSuffix,
			"enable_nat_gateway":  false,
			"enable_vpc_endpoints": false,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Verify public route table
	publicRouteTableID := terraform.Output(t, terraformOptions, "public_route_table_id")
	assert.NotEmpty(t, publicRouteTableID)

	// Verify private route tables (one per AZ)
	privateRouteTableIDs := terraform.OutputList(t, terraformOptions, "private_route_table_ids")
	assert.Len(t, privateRouteTableIDs, 3, "Expected 3 private route tables")
}

// TestVPCEndpointsEnabled verifies VPC endpoints are created when enabled
func TestVPCEndpointsEnabled(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/vpc",
		Vars: map[string]interface{}{
			"vpc_cidr":            "10.0.0.0/16",
			"environment":         environment,
			"name_suffix":         nameSuffix,
			"enable_nat_gateway":  false,
			"enable_vpc_endpoints": true, // Enable VPC endpoints
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Verify S3 endpoint
	s3EndpointID := terraform.Output(t, terraformOptions, "vpc_endpoint_s3_id")
	assert.NotEmpty(t, s3EndpointID)

	// Verify RDS endpoint
	rdsEndpointID := terraform.Output(t, terraformOptions, "vpc_endpoint_rds_id")
	assert.NotEmpty(t, rdsEndpointID)

	// Verify Bedrock endpoint
	bedrockEndpointID := terraform.Output(t, terraformOptions, "vpc_endpoint_bedrock_id")
	assert.NotEmpty(t, bedrockEndpointID)
}

// TestVPCEndpointsDisabled verifies VPC endpoints are not created when disabled
func TestVPCEndpointsDisabled(t *testing.T) {
	t.Parallel()

	uniqueID := random.UniqueId()
	environment := "dev"
	nameSuffix := strings.ToLower(fmt.Sprintf("test-%s", uniqueID))

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../modules/vpc",
		Vars: map[string]interface{}{
			"vpc_cidr":            "10.0.0.0/16",
			"environment":         environment,
			"name_suffix":         nameSuffix,
			"enable_nat_gateway":  false,
			"enable_vpc_endpoints": false, // Disable VPC endpoints
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndApply(t, terraformOptions)

	// Verify endpoints are empty
	s3EndpointID := terraform.Output(t, terraformOptions, "vpc_endpoint_s3_id")
	assert.Empty(t, s3EndpointID)

	rdsEndpointID := terraform.Output(t, terraformOptions, "vpc_endpoint_rds_id")
	assert.Empty(t, rdsEndpointID)

	bedrockEndpointID := terraform.Output(t, terraformOptions, "vpc_endpoint_bedrock_id")
	assert.Empty(t, bedrockEndpointID)
}
