#!/bin/bash
set -e

# Load environment variables from .env file
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
  echo "Loaded environment variables from .env file"
else
  echo "No .env file found. Please create one based on .env.example"
  exit 1
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
  print_error "AWS CLI is not installed. Please install it first."
  exit 1
fi

# Check if AWS account is configured
if ! aws sts get-caller-identity &> /dev/null; then
  print_error "AWS CLI is not configured. Please run 'aws configure' first."
  exit 1
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
print_message "Using AWS account: $ACCOUNT_ID"

# Account validation (optional)
if [[ "$ACCOUNT_ID" != "$AWS_ACCOUNT_ID" ]]; then
  print_error "Wrong AWS account. Expected: $AWS_ACCOUNT_ID, Got: $ACCOUNT_ID"
  exit 1
fi

# Create S3 bucket for deployment artifacts
BUCKET_NAME="${S3_BUCKET_SUFFIX}-${AWS_ACCOUNT_ID}"
print_message "Creating S3 bucket: $BUCKET_NAME"
if ! aws s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null; then
  aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION
else
  print_warning "Bucket already exists, using existing bucket"
fi

# Create a single deployment package with all Lambda functions
print_message "Creating a single deployment package for all Lambda functions"

# Create the build directory
mkdir -p .build

# Copy all Lambda function files from src directory
print_message "Copying Lambda function files"
for func in initializer batch_processor batch_submitter checker finalizer; do
  if [ -f "src/$func.py" ]; then
    cp src/$func.py .build/
    print_message "Copied $func.py to deployment package"
  else
    print_warning "$func.py not found, using placeholder"
    echo '# Placeholder Lambda function
def lambda_handler(event, context):
    return {"status": "placeholder", "message": "Replace with actual code"}' > .build/$func.py
  fi
done

# Copy shared modules
if [ -f "src/database.py" ]; then
  cp src/database.py .build/
  print_message "Copied database.py to deployment package"
fi

if [ -f "src/key_management.py" ]; then
  cp src/key_management.py .build/
  print_message "Copied key_management.py to deployment package"
fi

# Install dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
  print_message "Installing dependencies"
  pip install -r requirements.txt -t .build/ --quiet
fi

# Create the ZIP file
print_message "Creating deployment package ZIP file"
cd .build
zip -r ../deployment-package.zip . -q
cd ..

# Upload to S3
print_message "Uploading deployment package to S3"
aws s3 cp deployment-package.zip s3://$BUCKET_NAME/deployment-package.zip

# Deploy CloudFormation stack
print_message "Deploying CloudFormation stack: $STACK_NAME"

# Upload the CloudFormation template to S3
aws s3 cp cloudformattion.yaml s3://$BUCKET_NAME/cloudformation.yaml

# Check if stack exists
if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION &> /dev/null; then
  # Update existing stack
  print_message "Stack already exists. Updating stack..."

  aws cloudformation update-stack \
    --stack-name $STACK_NAME \
    --template-url https://s3.amazonaws.com/$BUCKET_NAME/cloudformation.yaml \
    --parameters \
      ParameterKey=BatchSize,ParameterValue=$BATCH_SIZE \
      ParameterKey=Concurrency,ParameterValue=$CONCURRENCY \
      ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
      ParameterKey=DeploymentBucket,ParameterValue=$BUCKET_NAME \
      ParameterKey=DeploymentPackageKey,ParameterValue=deployment-package.zip \
    --capabilities CAPABILITY_IAM \
    --region $AWS_REGION

  # Wait for stack update to complete
  print_message "Waiting for stack update to complete..."
  aws cloudformation wait stack-update-complete --stack-name $STACK_NAME --region $AWS_REGION
  UPDATE_RESULT=$?

  if [ $UPDATE_RESULT -eq 0 ]; then
    print_message "Stack update completed successfully!"
  else
    print_error "Stack update failed. Check the CloudFormation console for details."
    exit 1
  fi
else
  # Create new stack
  print_message "Creating new stack..."

  aws cloudformation create-stack \
    --stack-name $STACK_NAME \
    --template-url https://s3.amazonaws.com/$BUCKET_NAME/cloudformation.yaml \
    --parameters \
      ParameterKey=BatchSize,ParameterValue=$BATCH_SIZE \
      ParameterKey=Concurrency,ParameterValue=$CONCURRENCY \
      ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
      ParameterKey=DeploymentBucket,ParameterValue=$BUCKET_NAME \
      ParameterKey=DeploymentPackageKey,ParameterValue=deployment-package.zip \
    --capabilities CAPABILITY_IAM \
    --region $AWS_REGION

  # Wait for stack creation to complete
  print_message "Waiting for stack creation to complete (this may take 5-10 minutes)..."
  aws cloudformation wait stack-create-complete --stack-name $STACK_NAME --region $AWS_REGION
  CREATE_RESULT=$?

  if [ $CREATE_RESULT -eq 0 ]; then
    print_message "Stack creation completed successfully!"
  else
    print_error "Stack creation failed. Check the CloudFormation console for details."
    exit 1
  fi
fi

# Clean up build artifacts
print_message "Cleaning up build artifacts"
rm -rf .build
rm -f deployment-package.zip

# Get stack outputs
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' --output text --region $AWS_REGION)
QUEUE_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`BatchQueueUrl`].OutputValue' --output text --region $AWS_REGION)

print_message "Deployment completed with the following resources:"
echo "State Machine ARN: $STATE_MACHINE_ARN"
echo "SQS Queue URL: $QUEUE_URL"

# Instructions for starting the process
print_message "To start the record signing process, run:"
echo "aws stepfunctions start-execution \\"
echo "  --state-machine-arn $STATE_MACHINE_ARN \\"
echo "  --input '{\"batch_size\": $BATCH_SIZE, \"concurrency\": $CONCURRENCY}' \\"
echo "  --region $AWS_REGION"

print_message "Deployment script completed."
