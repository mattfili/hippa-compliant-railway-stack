# AWS Test Environment Setup Guide

This guide walks you through setting up your AWS environment to run the Terraform infrastructure tests for Feature 3.

## Prerequisites Checklist

Before you begin, ensure you have:

- [ ] AWS Account (free tier is sufficient for testing)
- [ ] Credit card on file with AWS (required even for free tier)
- [ ] Terminal access (macOS Terminal, Linux shell, or Windows WSL)
- [ ] ~30-60 minutes for initial setup
- [ ] ~$10-20 budget for test execution (one-time cost)

---

## Step 1: AWS Account Setup

### 1.1 Create AWS Account (if needed)

If you don't have an AWS account:

1. Go to https://aws.amazon.com/
2. Click "Create an AWS Account"
3. Follow the signup process:
   - Email address and password
   - Contact information
   - Credit card (won't be charged unless you exceed free tier)
   - Phone verification
   - Select "Basic Support - Free" plan

### 1.2 Sign Up for AWS BAA (for HIPAA compliance)

**IMPORTANT**: For production HIPAA compliance, you need a Business Associate Agreement:

1. Log into AWS Console: https://console.aws.amazon.com/
2. Navigate to: **AWS Artifact** service
3. Go to **Agreements** → **AWS Business Associate Addendum**
4. Download and review the BAA
5. Click **Accept Agreement**

This is required for HIPAA compliance but **not required for running tests**.

---

## Step 2: Create IAM User for Terraform

**DO NOT use your root AWS account credentials!** Create a dedicated IAM user:

### 2.1 Navigate to IAM Service

1. Log into AWS Console: https://console.aws.amazon.com/
2. Search for "IAM" in the top search bar
3. Click **IAM** (Identity and Access Management)

### 2.2 Create New User

1. Click **Users** in the left sidebar
2. Click **Create user** button
3. User name: `terraform-test-user`
4. Click **Next**

### 2.3 Attach Permissions

1. Select **Attach policies directly**
2. Search for and check these policies:
   - ✅ `AdministratorAccess` (for test environment - full access needed)

   **Note**: In production, you'd use more restrictive policies. For testing, AdministratorAccess is acceptable.

3. Click **Next**
4. Click **Create user**

### 2.4 Create Access Keys

1. Click on the newly created `terraform-test-user`
2. Go to **Security credentials** tab
3. Scroll to **Access keys** section
4. Click **Create access key**
5. Select use case: **Command Line Interface (CLI)**
6. Check "I understand the above recommendation" checkbox
7. Click **Next**
8. Description (optional): `Terraform testing`
9. Click **Create access key**

**IMPORTANT**: You'll see your credentials **only once**:
- **Access key ID**: Looks like `AKIAIOSFODNN7EXAMPLE`
- **Secret access key**: Looks like `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

**Save these securely!** We'll use them in the next step.

---

## Step 3: Install Required Tools

### 3.1 Install AWS CLI

**macOS** (using Homebrew):
```bash
brew install awscli
```

**Linux**:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows** (using PowerShell):
```powershell
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

Verify installation:
```bash
aws --version
# Should show: aws-cli/2.x.x ...
```

### 3.2 Install Terraform CLI

**macOS** (using Homebrew):
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

**Linux**:
```bash
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

**Windows** (using Chocolatey):
```powershell
choco install terraform
```

Verify installation:
```bash
terraform version
# Should show: Terraform v1.5.x or higher
```

### 3.3 Install Go Runtime (for Terratest)

**macOS** (using Homebrew):
```bash
brew install go
```

**Linux**:
```bash
wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc
```

**Windows** (using Chocolatey):
```powershell
choco install golang
```

Verify installation:
```bash
go version
# Should show: go version go1.21.x ...
```

---

## Step 4: Configure AWS Credentials

### 4.1 Configure AWS CLI Profile

Run the AWS configure command:

```bash
aws configure --profile terraform-test
```

When prompted, enter:
- **AWS Access Key ID**: (paste the Access key ID from Step 2.4)
- **AWS Secret Access Key**: (paste the Secret access key from Step 2.4)
- **Default region name**: `us-east-1` (or your preferred region)
- **Default output format**: `json`

### 4.2 Verify Credentials

Test that your credentials work:

```bash
aws sts get-caller-identity --profile terraform-test
```

You should see output like:
```json
{
    "UserId": "AIDAIOSFODNN7EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/terraform-test-user"
}
```

**Save your Account ID** - you'll need it for the next step!

### 4.3 Export Credentials as Environment Variables

Add to your `~/.bashrc`, `~/.zshrc`, or run in your current terminal:

```bash
export AWS_PROFILE=terraform-test
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=123456789012  # Replace with your account ID from step 4.2
```

Reload your shell:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

---

## Step 5: Bootstrap Terraform State Backend

The Terraform state backend (S3 + DynamoDB) must be created **before** running Terraform or tests.

### 5.1 Navigate to Terraform Directory

```bash
cd /Users/mattfili/Dev/hippa-compliant-railway-stack/terraform
```

### 5.2 Run Bootstrap Script

We'll create a helper script to automate this:

```bash
# Run the bootstrap script (we'll create this next)
bash scripts/bootstrap-state-backend.sh
```

This script will:
- Create S3 bucket for Terraform state: `terraform-state-dev-{account-id}`
- Enable versioning on the bucket
- Create DynamoDB table for state locking: `terraform-state-lock`
- Configure encryption

**Expected output:**
```
✓ Created S3 bucket: terraform-state-dev-123456789012
✓ Enabled versioning on state bucket
✓ Created DynamoDB table: terraform-state-lock
✓ State backend ready!
```

---

## Step 6: Initialize Terraform

### 6.1 Initialize Terraform Backend

```bash
cd /Users/mattfili/Dev/hippa-compliant-railway-stack/terraform
terraform init
```

**Expected output:**
```
Initializing the backend...
Successfully configured the backend "s3"!

Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.x.x...

Terraform has been successfully initialized!
```

### 6.2 Create Dev Workspace

```bash
terraform workspace new dev
terraform workspace select dev
```

**Expected output:**
```
Created and switched to workspace "dev"!
```

### 6.3 Validate Terraform Configuration

```bash
terraform validate
```

**Expected output:**
```
Success! The configuration is valid.
```

---

## Step 7: Run Terraform Tests

Now you're ready to run the infrastructure tests!

### 7.1 Navigate to Tests Directory

```bash
cd /Users/mattfili/Dev/hippa-compliant-railway-stack/terraform/tests
```

### 7.2 Download Go Dependencies

```bash
go mod download
```

### 7.3 Run Unit Tests (Individual Modules)

**VPC Module Test** (~5 minutes):
```bash
go test -v -timeout 30m ./unit/vpc_test.go
```

**Networking Module Test** (~3 minutes):
```bash
go test -v -timeout 30m ./unit/networking_test.go
```

**KMS Module Test** (~2 minutes):
```bash
go test -v -timeout 30m ./unit/kms_test.go
```

**S3 Module Test** (~3 minutes):
```bash
go test -v -timeout 30m ./unit/s3_test.go
```

**RDS Module Test** (~20 minutes - RDS is slow!):
```bash
go test -v -timeout 45m ./unit/rds_test.go
```

**IAM Module Test** (~2 minutes):
```bash
go test -v -timeout 30m ./unit/iam_test.go
```

**Config Module Test** (~3 minutes):
```bash
go test -v -timeout 30m ./unit/config_test.go
```

### 7.4 Run Integration Tests (Full Stack)

**⚠️ WARNING**: Integration tests deploy the entire infrastructure and take ~25 minutes to run!

```bash
go test -v -timeout 60m ./integration/full_stack_test.go
```

### 7.5 Run All Tests (Optional)

To run **all tests in parallel** (faster but uses more AWS resources):

```bash
go test -v -timeout 60m ./...
```

---

## Step 8: Monitor Costs

### 8.1 Enable Cost Explorer

1. Go to AWS Console: https://console.aws.amazon.com/
2. Search for "Cost Explorer"
3. Click **Enable Cost Explorer**

### 8.2 Set Up Billing Alerts

1. Go to **CloudWatch** service
2. Click **Alarms** → **Create alarm**
3. Select **Billing** metrics
4. Set threshold: `$20` (or your preferred limit)
5. Configure SNS notification to your email

### 8.3 Expected Test Costs

Running all tests once:
- **VPC**: ~$0.50 (NAT Gateway, VPC endpoints for ~5 minutes)
- **RDS**: ~$5-8 (db.t3.medium for ~20 minutes)
- **S3**: ~$0.10 (storage + requests)
- **Other**: ~$0.50 (KMS, Config, IAM - minimal)

**Total per test run**: ~$6-10

**Cost optimization tips**:
- Tests automatically clean up resources (`terraform destroy`)
- Run tests during weekdays (avoid weekend rates)
- Use `db.t3.micro` in dev environment (cheaper)

---

## Step 9: Cleanup After Testing

### 9.1 Verify All Resources Destroyed

After tests complete, verify cleanup:

```bash
aws ec2 describe-vpcs --profile terraform-test --region us-east-1 --filters "Name=tag:Environment,Values=dev"
aws rds describe-db-instances --profile terraform-test --region us-east-1
aws s3 ls --profile terraform-test
```

Should show minimal resources (only state backend bucket).

### 9.2 Delete State Backend (Optional)

If you're completely done testing and want to remove everything:

```bash
# Delete DynamoDB table
aws dynamodb delete-table --table-name terraform-state-lock --profile terraform-test

# Empty and delete S3 bucket
aws s3 rm s3://terraform-state-dev-${AWS_ACCOUNT_ID} --recursive --profile terraform-test
aws s3 rb s3://terraform-state-dev-${AWS_ACCOUNT_ID} --profile terraform-test
```

---

## Troubleshooting

### Issue: "Access Denied" Errors

**Cause**: IAM user lacks necessary permissions

**Solution**:
1. Go to IAM Console
2. Click your `terraform-test-user`
3. Verify `AdministratorAccess` policy is attached
4. Wait 5 minutes for permissions to propagate

### Issue: "Region Not Enabled"

**Cause**: Your AWS account doesn't have the specified region enabled

**Solution**:
1. Use `us-east-1` (always enabled by default)
2. Or enable your region: AWS Console → Account → Regions

### Issue: Tests Timeout

**Cause**: RDS provisioning can be slow

**Solution**:
- Increase timeout: `go test -v -timeout 60m ./unit/rds_test.go`
- Use smaller instance: Edit `terraform.tfvars.dev` → `db.t3.micro`

### Issue: State Lock Error

**Cause**: Previous test run didn't clean up lock

**Solution**:
```bash
# Force unlock (use the Lock ID from error message)
terraform force-unlock <LOCK_ID>
```

### Issue: "Bucket Already Exists"

**Cause**: S3 bucket names must be globally unique

**Solution**:
- Bucket names include your AWS account ID, so this shouldn't happen
- If it does, edit `terraform/backend.tf` and change bucket name

---

## Next Steps

Once tests are passing:

1. ✅ **Run CI/CD Pipeline**: Add AWS credentials to GitHub Secrets
2. ✅ **Deploy to Dev**: `terraform apply -var-file=terraform.tfvars.dev`
3. ✅ **Deploy to Staging**: Create staging workspace and apply
4. ✅ **Deploy to Production**: Create production workspace and apply
5. ✅ **Integrate with Railway**: Follow `docs/TERRAFORM_RAILWAY_INTEGRATION.md`

---

## Security Best Practices

- ✅ **Never commit credentials** to Git (they're in `.gitignore`)
- ✅ **Rotate access keys** every 90 days
- ✅ **Use MFA** on your root AWS account
- ✅ **Enable CloudTrail** for audit logging
- ✅ **Review IAM policies** regularly
- ✅ **Delete unused IAM users** when testing is complete

---

## Support

If you encounter issues:

1. Check `docs/TERRAFORM_TROUBLESHOOTING.md`
2. Review test output for specific error messages
3. Check AWS Console for resource state
4. Verify AWS credentials: `aws sts get-caller-identity`

For Feature 3 specific issues, see:
- `agent-os/specs/2025-10-17-aws-infrastructure-provisioning/verification/final-verification.md`
- `terraform/tests/TEST_COVERAGE.md`
