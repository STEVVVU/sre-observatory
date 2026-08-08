variable "name" {
  description = "Name prefix applied to network resources."
  type        = string
}

variable "vpc_cidr" {
  description = "IPv4 CIDR assigned to the VPC."
  type        = string
}

variable "availability_zones" {
  description = "Availability zones used for public and private subnets."
  type        = list(string)
  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least two availability zones are required."
  }
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs, one for each availability zone."
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs, one for each availability zone."
  type        = list(string)
}

variable "single_nat_gateway" {
  description = "Use one NAT gateway to reduce non-production cost; disable for AZ-level resilience."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags merged into every network resource."
  type        = map(string)
  default     = {}
}

