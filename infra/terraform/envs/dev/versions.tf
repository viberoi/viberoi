terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state in the bootstrap bucket. The bucket name format here
  # MUST match what `bootstrap/main.tf` produces:
  #   "${var.project}-tf-state-${var.account_id}"
  # If your account id differs, override via `-backend-config` during
  # `terraform init`:
  #   terraform init -backend-config="bucket=viberoi-tf-state-<your-id>"
  backend "s3" {
    key            = "envs/dev/main.tfstate"
    region         = "us-east-1"
    dynamodb_table = "viberoi-tf-lock"
    encrypt        = true
    # `bucket` intentionally unset — pass via:
    #   terraform init -backend-config="bucket=viberoi-tf-state-<account_id>"
    # so a single repo can target multiple AWS accounts without code edits.
  }
}
