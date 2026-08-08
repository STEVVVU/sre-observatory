variable "name" {
  description = "EKS cluster name."
  type        = string
}

variable "kubernetes_version" {
  description = "EKS Kubernetes minor version."
  type        = string
}

variable "vpc_id" {
  description = "VPC identifier."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnets used by the control plane and managed nodes."
  type        = list(string)
}

variable "instance_types" {
  description = "Allowed managed-node instance types."
  type        = list(string)
  default     = ["m7i.large"]
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 5
}

variable "access_entries" {
  description = "Explicit EKS API access entries. Keep empty until operator roles are known."
  type        = any
  default     = {}
}

variable "tags" {
  description = "Tags merged into cluster resources."
  type        = map(string)
  default     = {}
}

