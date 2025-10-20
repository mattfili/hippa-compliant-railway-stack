output "vpc_id" {
  value       = aws_vpc.main.id
  description = "VPC ID"
}

output "vpc_cidr_block" {
  value       = aws_vpc.main.cidr_block
  description = "VPC CIDR block"
}

output "private_subnet_ids" {
  value       = aws_subnet.private[*].id
  description = "Private subnet IDs for RDS and app endpoints"
}

output "public_subnet_ids" {
  value       = aws_subnet.public[*].id
  description = "Public subnet IDs for NAT gateways"
}

output "vpc_endpoint_s3_id" {
  value       = var.enable_vpc_endpoints ? aws_vpc_endpoint.s3[0].id : ""
  description = "S3 VPC endpoint ID"
}

output "vpc_endpoint_rds_id" {
  value       = var.enable_vpc_endpoints ? aws_vpc_endpoint.rds[0].id : ""
  description = "RDS VPC endpoint ID"
}

output "vpc_endpoint_bedrock_id" {
  value       = var.enable_vpc_endpoints ? aws_vpc_endpoint.bedrock[0].id : ""
  description = "Bedrock VPC endpoint ID"
}

output "nat_gateway_ids" {
  value       = aws_nat_gateway.main[*].id
  description = "NAT Gateway IDs"
}

output "internet_gateway_id" {
  value       = aws_internet_gateway.main.id
  description = "Internet Gateway ID"
}

output "private_route_table_ids" {
  value       = aws_route_table.private[*].id
  description = "Private route table IDs"
}

output "public_route_table_id" {
  value       = aws_route_table.public.id
  description = "Public route table ID"
}
