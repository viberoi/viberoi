output "vpc_id" {
  description = "VPC id - referenced by every other module that creates resources in the VPC."
  value       = aws_vpc.this.id
}

output "vpc_cidr_block" {
  description = "The VPC's primary CIDR. Security groups use this for cross-tier rules."
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "Subnets the ALB attaches to."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Subnets ECS Fargate tasks and Lambdas run in."
  value       = aws_subnet.private[*].id
}

output "data_subnet_ids" {
  description = "Subnets RDS and ElastiCache subnet groups live in."
  value       = aws_subnet.data[*].id
}

output "availability_zones" {
  description = "AZs the VPC spans, in stable order."
  value       = local.azs
}

output "nat_gateway_ids" {
  description = "NAT gateway ids - one or more depending on `single_nat`."
  value       = aws_nat_gateway.this[*].id
}
