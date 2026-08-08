output "vpc_id" {
  description = "VPC identifier."
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "Public subnet identifiers in input order."
  value       = [for index in range(length(var.public_subnet_cidrs)) : aws_subnet.public[tostring(index)].id]
}

output "private_subnet_ids" {
  description = "Private subnet identifiers in input order."
  value       = [for index in range(length(var.private_subnet_cidrs)) : aws_subnet.private[tostring(index)].id]
}

