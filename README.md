# Record Signing Service

A serverless, message-driven microservice solution for signing large volumes of records with a pool of cryptographic keys.

## Overview

This solution provides a scalable and efficient way to sign a large number of records (e.g., 100,000) using a collection of private keys (e.g., 100 keys) while ensuring:

- No double signing of records
- Safe key management (no concurrent use of the same key)
- Batch processing with configurable batch sizes
- Efficient key rotation using a least-recently-used strategy

The architecture uses AWS serverless services (Lambda, Step Functions, SQS, CloudFormation, DynamoDB) to create a highly scalable and resilient signing infrastructure.

## Architecture

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 600">
  <!-- Background -->
  <rect width="1000" height="600" fill="#f8f9fa"/>

  <!-- Title -->
  <text x="500" y="40" font-family="Arial" font-size="24" text-anchor="middle" font-weight="bold" fill="#232f3e">Record Signing Service Architecture</text>

  <!-- AWS Cloud Border -->
  <rect x="40" y="60" width="920" height="510" fill="#ffffff" stroke="#232f3e" stroke-width="2" rx="10" ry="10"/>
  <text x="65" y="85" font-family="Arial" font-size="18" fill="#232f3e">AWS Cloud</text>

  <!-- AWS CloudFormation -->
  <rect x="80" y="100" width="130" height="60" fill="#FF4F8B" stroke="#232f3e" stroke-width="2" rx="5" ry="5"/>
  <text x="145" y="135" font-family="Arial" font-size="14" text-anchor="middle" fill="white">CloudFormation</text>
  <text x="145" y="150" font-family="Arial" font-size="12" text-anchor="middle" fill="white">Template</text>

  <!-- Step Functions State Machine -->
  <rect x="400" y="100" width="200" height="80" fill="#cd5c5c" stroke="#232f3e" stroke-width="2" rx="5" ry="5"/>
  <text x="500" y="135" font-family="Arial" font-size="16" text-anchor="middle" fill="white">Step Functions</text>
  <text x="500" y="155" font-family="Arial" font-size="12" text-anchor="middle" fill="white">State Machine</text>
  <text x="500" y="170" font-family="Arial" font-size="10" text-anchor="middle" fill="white">(Record Signing Workflow)</text>

  <!-- Workflow States inside Step Functions -->
  <rect x="320" y="200" width="360" height="100" fill="#ffffff" stroke="#cd5c5c" stroke-width="2" rx="5" ry="5"/>
  <text x="500" y="220" font-family="Arial" font-size="12" text-anchor="middle" fill="#232f3e">Workflow States</text>

  <rect x="330" y="230" width="50" height="30" fill="#cd5c5c" stroke="#232f3e" stroke-width="1" rx="2" ry="2" opacity="0.8"/>
  <text x="355" y="250" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Initialize</text>

  <rect x="390" y="230" width="70" height="30" fill="#cd5c5c" stroke="#232f3e" stroke-width="1" rx="2" ry="2" opacity="0.8"/>
  <text x="425" y="250" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Check Records</text>

  <rect x="470" y="230" width="60" height="30" fill="#cd5c5c" stroke="#232f3e" stroke-width="1" rx="2" ry="2" opacity="0.8"/>
  <text x="500" y="250" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Submit</text>

  <rect x="540" y="230" width="60" height="30" fill="#cd5c5c" stroke="#232f3e" stroke-width="1" rx="2" ry="2" opacity="0.8"/>
  <text x="570" y="250" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Wait</text>

  <rect x="610" y="230" width="60" height="30" fill="#cd5c5c" stroke="#232f3e" stroke-width="1" rx="2" ry="2" opacity="0.8"/>
  <text x="640" y="250" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Complete</text>

  <path d="M 380 245 L 390 245" stroke="#232f3e" stroke-width="1" fill="none" marker-end="url(#arrowhead)"/>
  <path d="M 460 245 L 470 245" stroke="#232f3e" stroke-width="1" fill="none" marker-end="url(#arrowhead)"/>
  <path d="M 530 245 L 540 245" stroke="#232f3e" stroke-width="1" fill="none" marker-end="url(#arrowhead)"/>
  <path d="M 600 245 L 610 245" stroke="#232f3e" stroke-width="1" fill="none" marker-end="url(#arrowhead)"/>

  <!-- Lambda Function Group -->
  <rect x="80" y="320" width="200" height="220" fill="#f7f7f7" stroke="#232f3e" stroke-width="1" rx="5" ry="5"/>
  <text x="180" y="340" font-family="Arial" font-size="14" text-anchor="middle" fill="#232f3e">Lambda Functions</text>

  <!-- Initializer Lambda -->
  <rect x="100" y="350" width="160" height="40" fill="#FF9900" stroke="#232f3e" stroke-width="2" rx="5" ry="5"/>
  <text x="180" y="375" font-family="Arial" font-size="14" text-anchor="middle" fill="white">Initializer</text>

  <!-- Checker Lambda -->
  <rect x="100" y="400" width="160" height="40" fill="#FF9900" stroke="#232f3e" stroke-width="2" rx="5" ry="5"/>
  <text x="180" y="425" font-family="Arial" font-size="14" text-anchor="middle" fill="white">Checker</text>

  <!-- Batch Submitter Lambda -->
  <rect x="100" y="450" width="160" height="40" fill="#FF9900" stroke="#232f3e" stroke-width="2" rx="5" ry="5"/>
  <text x="180" y="475" font-family="Arial" font-size="14" text-anchor="middle" fill="white">Batch Submitter</text>

  <!-- Finalizer Lambda -->
  <rect x="100" y="500" width="160" height="30" fill="#FF9900" stroke="#232f3e" stroke-width="2" rx="5" ry="5"/>
  <text x="180" y="520" font-family="Arial" font-size="14" text-anchor="middle" fill="white">Finalizer</text>

  <!-- Messaging Services -->
  <rect x="320" y="320" width="160" height="190" fill="#f7f7f7" stroke="#232f3e" stroke-width="1" rx="5" ry="5"/>
  <text x="400" y="340" font-family="Arial" font-size="14" text-anchor="middle" fill="#232f3e">Messaging Services</text>

  <!-- SQS Queue -->
  <rect x="330" y="350" width="140" height="60" fill="#8c4fff" stroke="#232f3e" stroke-width="2" rx="5" ry="5"/>
  <text x="400" y="375" font-family="Arial" font-size="16" text-anchor="middle" fill="white">Batch Queue</text>
  <text x="400" y="395" font-family="Arial" font-size="12" text-anchor="middle" fill="white">SQS</text>

  <!-- Dead Letter Queue -->
  <rect x="330" y="420" width="140" height="40" fill="#8c4fff" stroke="#232f3e" stroke-width="2" rx="5" ry="5" opacity="0.7"/>
  <text x="400" y="445" font-family="Arial" font-size="12" text-anchor="middle" fill="white">Dead Letter Queue</text>

  <!-- SNS Topic -->
  <rect x="330" y="470" width="140" height="40" fill="#8c4fff" stroke="#232f3e" stroke-width="2" rx="5" ry="5"/>
  <text x="400" y="490" font-family="Arial" font-size="12" text-anchor="middle" fill="white">Notification Topic (SNS)</text>

  <!-- Batch Processor Lambda -->
  <rect x="520" y="350" width="160" height="60" fill="#FF9900" stroke="#232f3e" stroke-width="2" rx="5" ry="5"/>
  <text x="600" y="375" font-family="Arial" font-size="16" text-anchor="middle" fill="white">Batch Processor</text>
  <text x="600" y="395" font-family="Arial" font-size="12" text-anchor="middle" fill="white">Lambda</text>

  <!-- DynamoDB Table -->
  <path d="M 520,450 L 680,450 L 700,470 L 680,490 L 520,490 L 500,470 Z" fill="#3b48cc" stroke="#232f3e" stroke-width="2"/>
  <text x="600" y="475" font-family="Arial" font-size="14" text-anchor="middle" fill="white">Key Usage Tracking</text>
  <text x="600" y="490" font-family="Arial" font-size="12" text-anchor="middle" fill="white">DynamoDB</text>

  <!-- RDS/PostgreSQL -->
  <rect x="720" y="350" width="160" height="60" fill="#3b48cc" stroke="#232f3e" stroke-width="2" rx="5" ry="5"/>
  <text x="800" y="375" font-family="Arial" font-size="14" text-anchor="middle" fill="white">Records Database</text>
  <text x="800" y="395" font-family="Arial" font-size="12" text-anchor="middle" fill="white">PostgreSQL</text>

  <!-- AWS Secrets Manager -->
  <rect x="720" y="450" width="160" height="40" fill="#3b48cc" stroke="#232f3e" stroke-width="2" rx="5" ry="5" opacity="0.8"/>
  <text x="800" y="475" font-family="Arial" font-size="14" text-anchor="middle" fill="white">Secrets Manager</text>

  <!-- Connection Lines -->
  <!-- Define arrowhead marker -->
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#232f3e"/>
    </marker>
  </defs>

  <!-- CloudFormation to all resources (dotted line) -->
  <path d="M 145 160 L 500 60" stroke="#232f3e" stroke-width="1.5" fill="none" stroke-dasharray="5,5"/>
  <text x="340" y="90" font-family="Arial" font-size="10" fill="#232f3e" text-anchor="middle">Provisions all resources</text>

  <!-- Step Functions to Lambda Functions -->
  <path d="M 400 180 L 200 350" stroke="#232f3e" stroke-width="1.5" fill="none" marker-end="url(#arrowhead)"/>
  <text x="310" y="250" font-family="Arial" font-size="10" fill="#232f3e" text-anchor="middle">Orchestrates</text>

  <!-- Batch Submitter to SQS -->
  <path d="M 260 470 L 330 380" stroke="#232f3e" stroke-width="1.5" fill="none" marker-end="url(#arrowhead)"/>
  <text x="290" y="420" font-family="Arial" font-size="10" fill="#232f3e" text-anchor="middle">Submits batches</text>

  <!-- SQS to Batch Processor -->
  <path d="M 470 380 L 520 380" stroke="#232f3e" stroke-width="1.5" fill="none" marker-end="url(#arrowhead)"/>
  <text x="495" y="365" font-family="Arial" font-size="10" fill="#232f3e" text-anchor="middle">Triggers</text>

  <!-- Batch Processor to DynamoDB -->
  <path d="M 600 410 L 600 450" stroke="#232f3e" stroke-width="1.5" fill="none" marker-end="url(#arrowhead)"/>
  <text x="620" y="430" font-family="Arial" font-size="10" fill="#232f3e" text-anchor="middle">Manages keys</text>

  <!-- Batch Processor to PostgreSQL -->
  <path d="M 680 380 L 720 380" stroke="#232f3e" stroke-width="1.5" fill="none" marker-end="url(#arrowhead)"/>
  <text x="700" y="365" font-family="Arial" font-size="10" fill="#232f3e" text-anchor="middle">Signs records</text>

  <!-- PostgreSQL to Secrets Manager -->
  <path d="M 800 410 L 800 450" stroke="#232f3e" stroke-width="1.5" fill="none" marker-end="url(#arrowhead)"/>
  <text x="830" y="430" font-family="Arial" font-size="10" fill="#232f3e" text-anchor="middle">Credentials</text>

  <!-- Finalizer to SNS -->
  <path d="M 260 515 L 330 490" stroke="#232f3e" stroke-width="1.5" fill="none" marker-end="url(#arrowhead)"/>
  <text x="300" y="520" font-family="Arial" font-size="10" fill="#232f3e" text-anchor="middle">Notifies</text>

  <!-- Legend -->
  <rect x="720" y="100" width="200" height="130" fill="white" stroke="#232f3e" stroke-width="1" rx="5" ry="5"/>
  <text x="820" y="120" font-family="Arial" font-size="14" text-anchor="middle" fill="#232f3e">Legend</text>

  <rect x="730" y="130" width="20" height="20" fill="#FF9900" stroke="#232f3e" stroke-width="1"/>
  <text x="770" y="145" font-family="Arial" font-size="12" fill="#232f3e">Lambda Functions</text>

  <rect x="730" y="155" width="20" height="20" fill="#cd5c5c" stroke="#232f3e" stroke-width="1"/>
  <text x="770" y="170" font-family="Arial" font-size="12" fill="#232f3e">Step Functions</text>

  <rect x="730" y="180" width="20" height="20" fill="#8c4fff" stroke="#232f3e" stroke-width="1"/>
  <text x="770" y="195" font-family="Arial" font-size="12" fill="#232f3e">Messaging (SQS/SNS)</text>

  <rect x="730" y="205" width="20" height="20" fill="#3b48cc" stroke="#232f3e" stroke-width="1"/>
  <text x="770" y="220" font-family="Arial" font-size="12" fill="#232f3e">Database Services</text>
</svg>


### Components

1. **CloudFormation Stack**: Infrastructure as code defining all AWS resources
2. **Step Functions State Machine**: Orchestrates the workflow with the following states:
   - Initialize → Check Remaining Records → Submit Batches → Wait → Check Remaining Records → Complete
3. **SQS Queue**: Distributes batches for processing with visibility timeout and dead-letter queue
4. **Lambda Functions**:
   - **Initializer**: Sets up the database and key store, counts remaining unsigned records
   - **Batch Submitter**: Creates batches and submits them to SQS
   - **Batch Processor**: Signs records in a batch using a single key
   - **Checker**: Counts remaining unsigned records
   - **Finalizer**: Generates completion notification and reports
5. **DynamoDB**: Tracks key usage to implement least-recently-used strategy
6. **SNS Topic**: Sends notifications when the signing process completes
7. **PostgreSQL Database**: Stores records and signatures (accessed via AWS Secrets Manager)

## Key Features

- **Concurrent Processing**: Processes multiple batches simultaneously while ensuring no key is used concurrently
- **Least Recently Used Key Selection**: Distributes key usage evenly
- **Error Handling**: Includes retries, dead-letter queues, and error reporting
- **Monitoring**: Comprehensive logging and status tracking
- **Notification**: Email notifications on completion via SNS
- **Security**: Secure database credentials via AWS Secrets Manager

## Requirements

- AWS CLI configured with appropriate permissions
- Python 3.9.6
- AWS account with access to:
  - Lambda
  - Step Functions
  - SQS
  - SNS
  - DynamoDB
  - CloudFormation
  - Secrets Manager
  - KMS (for key operations)
- PostgreSQL database (credentials stored in Secrets Manager)

## Configuration

Create a `.env` file in the project root with the following variables:

```
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
S3_BUCKET_SUFFIX=record-signing-deployment

# Stack Configuration
STACK_NAME=record-signing-service
ENVIRONMENT=dev

# Processing Configuration
BATCH_SIZE=1000
CONCURRENCY=10

# DB Creds AWS Secret
DB_SECRET_NAME=
```

## Deployment

### Initial Deployment

To deploy the solution for the first time:

```bash
./deploy.sh
```

This script will:
1. Load environment variables from `.env`
2. Validate AWS CLI installation and credentials
3. Create an S3 bucket for deployment artifacts
4. Package Lambda functions and dependencies
5. Upload the deployment package to S3
6. Deploy the CloudFormation stack
7. Output the ARN of the Step Function and SQS queue URL

### Cleanup

To delete all resources:

```bash
./cleanup.sh
```

This will:
1. Load environment variables from `.env`
2. Delete the CloudFormation stack
3. Empty and delete the S3 bucket
4. Clean up any remaining resources (Lambda functions, SQS queues)
5. Remove local deployment files

## Usage

After deployment, you can start the record signing process using the AWS CLI or AWS Console:

```bash
aws stepfunctions start-execution \
  --state-machine-arn <STATE_MACHINE_ARN> \
  --input '{"batch_size": 1000, "concurrency": 10}' \
  --region <AWS_REGION>
```

You can monitor the progress through the AWS Step Functions console.

## Implementation Details

### Database Schema

The solution uses a PostgreSQL database with the following schema:

```sql
CREATE TABLE IF NOT EXISTS records (
    id SERIAL PRIMARY KEY,
    data TEXT NOT NULL,
    signature TEXT,
    signed_at TIMESTAMP,
    signed_by TEXT
)
```

### Key Management

The `KeyManagementService` class (referenced in code) handles:
- Key acquisition to ensure no concurrent use
- Least-recently-used selection strategy
- Key release after batch signing
- Signing operations

DynamoDB is used to track key usage timestamps to implement the LRU strategy.

### Batch Processing Flow

1. **Initialization**: The Step Function starts with the Initializer Lambda
2. **Batch Submission**: The Batch Submitter sends batches to the SQS queue
3. **Processing**: The Batch Processor Lambda signs records using acquired keys
4. **Status Checking**: The Checker Lambda counts remaining unsigned records
5. **Completion**: The Finalizer Lambda notifies of process completion

## CloudFormation Resources

The CloudFormation template (`cloudformattion.yaml`) provisions:

1. **DynamoDB Table**: Tracks key usage
2. **SNS Topic & Subscription**: For completion notifications
3. **SQS Queue & Dead Letter Queue**: For batch processing
4. **Lambda Functions**: All required processing functions
5. **IAM Roles & Policies**: Necessary permissions
6. **Step Functions State Machine**: Workflow orchestration
7. **Event Source Mapping**: Connects SQS to Lambda

## Troubleshooting

- **CloudWatch Logs**: Each Lambda function has its own log group
- **Dead Letter Queue**: Check for failed batch processing messages
- **Step Functions Execution History**: Visual workflow showing the execution path
- **SNS Notifications**: Check for completion emails

## Security Considerations

- Database credentials stored in AWS Secrets Manager
- IAM roles following least privilege principle
- Lambda functions running in secure VPC (if configured)
- Key management ensuring no key overuse

## Development and Customization

To modify the solution:

1. Update the Lambda function code in the corresponding Python files
2. Modify the CloudFormation template as needed
3. Re-run `./deploy.sh` to deploy changes

### Adding Custom Processing Logic

To add custom processing logic, modify the `batch_processor.py` file to implement your specific signing algorithm or add additional validation steps.

### Scaling Considerations

- Adjust `BATCH_SIZE` and `CONCURRENCY` based on workload
- Increase Lambda memory allocation for faster processing
- Add VPC configuration for database access if needed
