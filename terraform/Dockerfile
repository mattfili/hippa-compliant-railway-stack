# ==============================================================================
# Terraform Dockerfile for Railway Deployment
# ==============================================================================
# This Dockerfile creates a container for running Terraform in Railway's
# deployment environment, provisioning AWS infrastructure and exporting outputs
# for the backend application.
# ==============================================================================

FROM hashicorp/terraform:1.5

# Install jq for JSON parsing
RUN apk add --no-cache jq

# Set working directory
WORKDIR /terraform

# Copy Terraform configuration files
COPY . /terraform/

# Create output directory
RUN mkdir -p /app

# Set environment variables for AWS credentials
# These will be passed from Railway environment variables:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - AWS_REGION
# - ENVIRONMENT (dev/staging/production)

# The start command is configured in railway.json:
# terraform init && terraform workspace select $ENVIRONMENT && terraform apply -auto-approve && terraform output -json > /app/outputs.json
