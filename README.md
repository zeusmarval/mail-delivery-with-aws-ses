# Mail Delivery with AWS SES

This repository contains a serverless application built with AWS SAM that implements email delivery using AWS SES via AWS Lambda with support for attachments.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Deployment](#deployment)
- [Usage](#usage)
  - [Event Structure](#event-structure)
  - [Testing Locally](#testing-locally)
  - [Invoking the Function](#invoking-the-function)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Lambda Function](#lambda-function)
- [Limits and Validations](#limits-and-validations)
- [Clean Up](#clean-up)
- [References](#references)

## Overview

This serverless application provides a complete solution for sending emails via AWS SES. The SAM template creates the following AWS resources:

- **AWS Lambda Function**: Function to send emails via AWS SES with support for attachments
- **CloudWatch Log Groups**: Log groups with configurable retention per environment (1 day for dev/qa, 7 days for prod)

## Features

- **Email Sending**: Send emails via AWS SES using the `send_raw_email` API
- **Attachment Support**: Support for multiple file attachments with automatic base64 decoding
- **HTML and Plain Text**: Support for both HTML and plain text email bodies
- **Multiple Recipients**: Support for To, CC, and BCC recipients (up to 50 total)
- **Reply-To Support**: Configure reply-to addresses for emails
- **Input Validation**: Comprehensive validation of email addresses, message size, and attachment limits
- **Error Handling**: Detailed error handling with specific error codes and messages
- **Structured Logging**: JSON-formatted logs with privacy protection (sensitive data is not logged)
- **Multiple Environments**: Support for dev, qa, and prod environments via parameters

## Prerequisites

- An AWS account
- AWS CLI configured with appropriate permissions
- AWS SAM CLI installed
- Python 3.13 (Lambda function runtime)
- Docker (optional, for builds with `--use-container`)
- AWS SES configured and verified (sender email addresses must be verified in SES)

## Installation

1. **Clone the repository:**

```bash
git clone <repository-url>
cd mail-delivery-with-aws-ses
```

2. **Install Lambda function dependencies:**

Dependencies are automatically installed during SAM build. The Lambda function uses:

- `boto3` (included in Lambda runtime)
- Python standard library (`email.mime`, `base64`, `logging`)

## Deployment

### Option 1: Using AWS SAM CLI (Recommended)

1. **Build the application:**

```bash
sam build --use-container
```

2. **Deploy the stack:**

```bash
sam deploy
```

The `sam deploy` command uses the configuration in `samconfig.toml`. To deploy to a different environment, you can modify the file or use parameters:

```bash
sam deploy --parameter-overrides Environment=qa
```

### Option 2: Using AWS CloudFormation directly

```bash
sam build --use-container
sam package --output-template-file packaged.yaml --s3-bucket YOUR_S3_BUCKET
aws cloudformation deploy \
    --template-file packaged.yaml \
    --stack-name dev-mail-delivery \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides Environment=dev
```

### Stack Parameters

- **Environment**: Deployment environment (dev, qa, prod). Default: `dev`
  - **dev/qa**: Log retention of 1 day
  - **prod**: Log retention of 7 days

**Important**: Before deploying, ensure that:
- Your sender email addresses are verified in AWS SES
- If your SES account is in sandbox mode, recipients must also be verified

## Usage

### Event Structure

The Lambda function expects a JSON event with the following structure:

#### Required Fields

- `from`: Sender email address (string)
- `to`: List of recipient email addresses (array of strings)
- `subject`: Email subject (string)
- `text`: Plain text version of the email body (string)
- `html`: HTML version of the email body (string)

#### Optional Fields

- `cc`: List of CC email addresses (array of strings)
- `bcc`: List of BCC email addresses (array of strings)
- `replyTo`: Reply-to email address(es) (string or array of strings)
- `attachments`: List of attachments (array of objects)

#### Attachment Object Structure

```json
{
  "filename": "example.pdf",
  "content": "base64_encoded_content",
  "contentType": "application/pdf"
}
```

**Fields:**
- `filename`: Name of the attachment file (required)
- `content`: Base64-encoded file content (required)
- `contentType`: MIME type of the file (optional, defaults to "application/octet-stream")

### Testing Locally

1. **Build the application:**

```bash
sam build
```

2. **Invoke the function with an example event:**

```bash
# Test without attachment
sam local invoke MailDeliveryFunction -e events/event-without-attachment.json

# Test with attachment
sam local invoke MailDeliveryFunction -e events/event-with-attachment.json
```

### Invoking the Function

#### Via AWS CLI

```bash
aws lambda invoke \
  --function-name <stack-name>-mail-delivery \
  --payload file://events/event-without-attachment.json \
  response.json
```

#### Via SDK

```python
import boto3
import json

lambda_client = boto3.client('lambda')

with open('events/event-without-attachment.json', 'r') as f:
    event = json.load(f)

response = lambda_client.invoke(
    FunctionName='<stack-name>-mail-delivery',
    InvocationType='RequestResponse',
    Payload=json.dumps(event)
)
```

## Project Structure

```
mail-delivery-with-aws-ses/
├── src/
│   └── lambdas/
│       └── email-delivery/        # Lambda function for email delivery
│           ├── app.py              # Main handler with validation
│           └── mail_options.py     # MIME message generation
├── events/                         # Test events for local testing
│   ├── event-without-attachment.json
│   └── event-with-attachment.json
├── template.yml                    # SAM/CloudFormation template
├── samconfig.toml                  # SAM CLI configuration
└── README.md
```

## Configuration

### Lambda Function Configuration

- **Handler**: `app.lambda_handler`
- **Runtime**: Python 3.13
- **Timeout**: 25 seconds
- **Architecture**: x86_64

### IAM Policies

The Lambda function has the following permissions:

- **Actions**:
  - `ses:SendEmail` - Send emails via SES
  - `ses:SendRawEmail` - Send raw emails with attachments via SES
- **Resource**: `*` (all SES resources)

**Note**: The function uses `send_raw_email` which supports attachments. The `send_email` permission is included for compatibility but is not used by the current implementation.

## Lambda Function

### Mail Delivery Function

**Description**: Sends emails via AWS SES with support for attachments, HTML/text content, and multiple recipients.

- **Handler**: `app.lambda_handler`
- **Runtime**: Python 3.13
- **Timeout**: 25 seconds

**Function flow:**
1. Validates all required fields and email formats
2. Validates message and attachment sizes against SES limits
3. Creates a properly formatted MIME message with text/HTML body and attachments
4. Sends the raw email via AWS SES `send_raw_email` API
5. Returns the SES MessageId on success or detailed error information on failure

**Response format:**

**Success:**
```json
{
  "statusCode": 200,
  "result": {
    "MessageId": "0100018a-f0c1-4a3b-9c2d-1e3f4a5b6c7d-000000"
  }
}
```

**Error:**
```json
{
  "statusCode": 400,
  "error": {
    "message": "Invalid 'from' email address: invalid-email",
    "type": "ValidationError"
  }
}
```

## Limits and Validations

### SES Limits

- **Maximum Recipients**: 50 total recipients (To + Cc + Bcc combined)
- **Maximum Message Size**: 10MB total message size
- **Maximum Attachment Size**: 10MB per attachment

### Validations

- **Email Format**: All email addresses are validated using regex pattern
- **Required Fields**: All required fields must be present and non-empty
- **Attachment Validation**: 
  - Filename must be present and non-empty
  - Content must be present and non-empty
  - Size validation before message generation
- **Message Size**: Total message size is validated before sending

## Clean Up

To delete the CloudFormation stack and all created resources:

```bash
sam delete --stack-name <environment>-<project>
```

Or using AWS CLI:

```bash
aws cloudformation delete-stack --stack-name <environment>-<project>
```

## References

- [AWS Serverless Application Model (SAM)](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html)
- [AWS SES Documentation](https://docs.aws.amazon.com/ses/latest/dg/Welcome.html)
- [AWS SES SendRawEmail API](https://docs.aws.amazon.com/ses/latest/APIReference/API_SendRawEmail.html)
- [CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html)
- [Python email.mime Documentation](https://docs.python.org/3/library/email.mime.html)
