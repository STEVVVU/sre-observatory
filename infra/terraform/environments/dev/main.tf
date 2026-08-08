provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.tags
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  tags = {
    Environment = "dev"
    ManagedBy   = "terraform"
    Project     = "sre-observatory"
  }
  access_entries = var.operator_role_arn == null ? {} : {
    operator = {
      principal_arn = var.operator_role_arn
      policy_associations = {
        cluster_admin = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = {
            type = "cluster"
          }
        }
      }
    }
  }
}

module "network" {
  source = "../../modules/network"

  name                 = var.cluster_name
  vpc_cidr             = "10.42.0.0/16"
  availability_zones   = slice(data.aws_availability_zones.available.names, 0, 3)
  public_subnet_cidrs  = ["10.42.0.0/24", "10.42.1.0/24", "10.42.2.0/24"]
  private_subnet_cidrs = ["10.42.16.0/20", "10.42.32.0/20", "10.42.48.0/20"]
  single_nat_gateway   = var.single_nat_gateway
  tags                 = local.tags
}

module "cluster" {
  source = "../../modules/cluster"

  name               = var.cluster_name
  kubernetes_version = var.kubernetes_version
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  access_entries     = local.access_entries
  tags               = local.tags
}
