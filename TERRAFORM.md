# Terraform Setup and Usage Guide

## Prerequisites

- [Terraform CLI](https://developer.hashicorp.com/terraform/downloads) installed
- AWS CLI configured with appropriate credentials
- Git installed (for version control)

## AWS Credentials Setup

Your AWS credentials should be configured in `~/.aws/credentials`. The file should look like this:

```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

For multiple AWS profiles, you can add additional sections:

```ini
[development]
aws_access_key_id = DEV_ACCESS_KEY
aws_secret_access_key = DEV_SECRET_KEY

[production]
aws_access_key_id = PROD_ACCESS_KEY
aws_secret_access_key = PROD_SECRET_KEY
```

To use a specific profile with Terraform, you can:
1. Set it in your terminal:
```bash
export AWS_PROFILE=development
```

2. Or specify it in your Terraform configuration (main.tf):
```hcl
provider "aws" {
  shared_credentials_files = ["~/.aws/credentials"]
  profile                 = "development"
  region                  = "us-west-2"
}
```

> **Note**: We specifically use `shared_credentials_files` to explicitly point to the credentials file location. This is more reliable than letting Terraform auto-discover credentials, especially in CI/CD environments or when working with multiple AWS configurations.

## Project Structure 

```
.
├── infra
│   ├── iam.tf
│   ├── lambda.tf
│   ├── main.tf
```

## Common Terraform Commands

1. Initialize Terraform in your project directory:
```bash
terraform init
```

2. Review planned changes:
```bash
terraform plan
```

3. Apply the infrastructure changes:
```bash
terraform apply
```
When prompted, type `yes` to confirm the changes.

4. Destroy infrastructure when no longer needed:
```bash
terraform destroy
```

## Best Practices

- Always run `terraform plan` before applying changes
- Use version control for your Terraform files
- Store terraform.tfstate file in a shared backend (like S3) for team collaboration
- Never commit sensitive information or .tfstate files to version control

## Useful Additional Commands

```bash
# Format terraform files
terraform fmt

# Validate terraform configuration
terraform validate

# Show current state
terraform show

# List all resources in state
terraform state list
```
