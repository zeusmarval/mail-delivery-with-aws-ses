# Mail Delivery With AWS SES

This repository contains an AWS CloudFormation template to set up a serverless application for sending emails using AWS Lambda and Amazon SES.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Deployment](#deployment)
- [Usage](#usage)
  - [Lambda Function](#lambda-function)
  - [IAM Policies](#iam-policies)
  - [Secret Management](#secret-management)
  - [VPC Configuration](#vpc-configuration)
- [Clean Up](#clean-up)
- [References](#references)

## Overview

The template provisions the following AWS resources:

- **AWS Lambda**: A function to send emails using Amazon SES.
- **AWS Secrets Manager**: Stores SMTP credentials securely.

## Features

- **Email Sending**: Utilizes Amazon SES for sending emails.
- **Secure Configuration**: Uses AWS Secrets Manager to store SMTP credentials securely.
- **VPC Integration**: Configured to run inside a specified VPC with security group and subnet settings.

## Prerequisites

- An AWS account.
- AWS CLI configured with appropriate permissions.
- Python 3.12 runtime environment.

## Deployment

1. **Clone the repository:**

    ```sh
    git clone https://github.com/zeusmarval/mail-delivery-with-aws-ses.git
    cd mail-delivery-with-aws-ses
    ```

2. **Package the stack:**

    ```sh
    sam build --use-container
    ```

3. **Deploy the CloudFormation stack:**

    ```sh
    aws cloudformation deploy \
        --template-file template.yaml \
        --stack-name SendEmailsViaSES \
        --capabilities CAPABILITY_NAMED_IAM
    ```

## Usage

### Lambda Function

- **Handler**: The entry point for the Lambda function is defined in the `app.lambda_handler` file located in the `src/mailDeliveryFunction` directory.
- **Runtime**: Python 3.12 is used as the runtime environment.

### IAM Policies

The Lambda function has the following permissions:

- **Actions**:
  - `ses:SendEmail`
  - `ses:SendRawEmail`
  - `secretsmanager:GetSecretValue`
- **Resource**: Specific to the SES and Secrets Manager resources required.

### Secret Management

- **AWS Secrets Manager**: Stores the SMTP credentials securely with the following parameters:
  - `SMTP_PASS`: SMTP password
  - `SMTP_PORT`: SMTP port
  - `SMTP_SERVER`: SMTP server address
  - `SMTP_USER`: SMTP username

### VPC Configuration

The Lambda function is configured to run within a VPC, using the following parameters:

- **Subnet IDs**: `subnet-1, subnet-2`
- **Security Group IDs**: `sg-000000`

## Clean Up

To delete the CloudFormation stack and all resources created:

```sh
aws cloudformation delete-stack --stack-name SendEmailsViaSES
```

## References

- Sending emails with Amazon SES: [Amazon SES Developer Guide](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-email.html)
- AWS Lambda with VPC: [AWS Lambda VPC Configuration](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html)
- AWS Secrets Manager: [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
