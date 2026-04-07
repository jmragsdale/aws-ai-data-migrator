terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment and configure for remote state management
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "aws-ai-data-migrator/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-locks"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.tags
  }
}

# S3 Bucket Module
module "s3" {
  source = "./modules/s3"

  bucket_name         = var.s3_bucket_name != "" ? var.s3_bucket_name : "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}"
  enable_versioning   = var.enable_versioning
  enable_encryption   = var.enable_encryption
  block_public_access = true

  lifecycle_rules = [
    {
      id            = "archive-old-objects"
      days          = 90
      storage_class = "GLACIER"
    },
    {
      id            = "delete-old-archives"
      days          = 365
      storage_class = "DELETE"
    }
  ]

  tags = var.tags
}

# DynamoDB Table Module
module "dynamodb" {
  source = "./modules/dynamodb"

  table_name             = "${var.project_name}-${var.dynamodb_table_name}"
  partition_key_name     = "id"
  partition_key_type     = "S"
  sort_key_name          = "timestamp"
  sort_key_type          = "S"
  billing_mode           = "PAY_PER_REQUEST"
  enable_pitr            = true
  enable_encryption      = var.enable_encryption
  point_in_time_recovery = true

  global_secondary_indexes = [
    {
      name            = "timestamp-index"
      partition_key   = "timestamp"
      partition_type  = "S"
      projection_type = "ALL"
    }
  ]

  tags = var.tags
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
