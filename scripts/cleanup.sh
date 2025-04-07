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
BUCKET_NAME="${S3_BUCKET_SUFFIX}-${AWS_ACCOUNT_ID}"

# Account validation (optional)
if [[ "$ACCOUNT_ID" != "$AWS_ACCOUNT_ID" ]]; then
  print_error "Wrong AWS account. Expected: $AWS_ACCOUNT_ID, Got: $ACCOUNT_ID"
  exit 1
fi

# Check if the stack exists
if ! aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION &> /dev/null; then
  print_warning "Stack $STACK_NAME doesn't exist. Nothing to clean up for CloudFormation."
else
  # Delete the CloudFormation stack
  print_message "Deleting CloudFormation stack: $STACK_NAME"
  aws cloudformation delete-stack --stack-name $STACK_NAME --region $AWS_REGION

  print_message "Waiting for stack deletion to complete (this may take 10-15 minutes)..."
  aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $AWS_REGION

  if [ $? -eq 0 ]; then
    print_message "Stack deletion completed successfully!"
  else
    print_error "Stack deletion may have encountered issues. Please check the CloudFormation console."
  fi
fi

# Clean up S3 bucket
if aws s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null; then
  print_message "Cleaning up S3 bucket: $BUCKET_NAME"
  aws s3 rm s3://$BUCKET_NAME --recursive
  aws s3 rb s3://$BUCKET_NAME
  print_message "S3 bucket deleted successfully!"
else
  print_warning "S3 bucket $BUCKET_NAME doesn't exist. Nothing to clean up for S3."
fi

# Additional cleanup
print_message "Checking for any remaining resources..."

# Look for Lambda functions that might be left over
lambda_functions=$(aws lambda list-functions --query "Functions[?starts_with(FunctionName, '$STACK_NAME')].FunctionName" --output text --region $AWS_REGION)
if [ ! -z "$lambda_functions" ]; then
  print_warning "Found Lambda functions that might be related to this project:"
  echo $lambda_functions

  echo -n "Do you want to delete these Lambda functions? (y/n): "
  read response
  if [[ "$response" =~ ^[Yy]$ ]]; then
    for func in $lambda_functions; do
      print_message "Deleting Lambda function: $func"
      aws lambda delete-function --function-name $func --region $AWS_REGION
    done
  fi
fi

# Clean up local deployment files
print_message "Cleaning up local deployment files..."
rm -rf .build
rm -f deployment-package.zip

print_message "Cleanup completed successfully!"
print_message "Note: If you've created any custom resources manually, you may need to remove them separately."
