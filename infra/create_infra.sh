#!/bin/bash
set -e

# Configurable values
REGION="us-west-2"
BUCKET_NAME="dlyogipchecker-bucket"
ROLE_NAME="dlyogipchecker-lambda-role"
LAMBDA_NAME="dlyogipchecker"
ZIP_FILE="lambda.zip"

echo "✅ Starting infrastructure setup..."

# 1. Create S3 bucket if not exists
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
  echo "☑️  S3 bucket $BUCKET_NAME already exists."
else
  aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"
  echo "✅ Created S3 bucket: $BUCKET_NAME"
fi

# 2. Create IAM Role if not exists
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document file://infra/trust-policy.json
  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  echo "✅ Created IAM role: $ROLE_NAME"
else
  echo "☑️  IAM Role $ROLE_NAME already exists."
fi

