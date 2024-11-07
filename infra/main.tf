terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region                   = "ap-southeast-1" # Change this to your desired region
  shared_credentials_files = ["~/.aws/credentials"]
  profile                  = "default" # Change this if using a different profile

  assume_role {
    role_arn = "arn:aws:iam::838835070561:role/url-shortener-lambda"
  }
}
