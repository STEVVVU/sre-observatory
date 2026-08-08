variable "aws_region" {
  description = "AWS region for the development platform."
  type        = string
  default     = "us-west-2"
}

variable "cluster_name" {
  description = "EKS cluster name and resource prefix."
  type        = string
  default     = "sre-observatory-dev"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes minor version; review supported versions before applying."
  type        = string
  default     = "1.31"
}

variable "operator_role_arn" {
  description = "IAM role granted cluster-administrator access. No access is created when null."
  type        = string
  default     = null
  nullable    = true
}

variable "single_nat_gateway" {
  description = "Use one NAT gateway for this cost-conscious development environment."
  type        = bool
  default     = true
}

