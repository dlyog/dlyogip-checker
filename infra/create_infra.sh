#!/bin/bash
set -e

# Configurable values
REGION="us-west-2"
BUCKET_NAME="dlyogipchecker-bucket"
LAMBDA_NAME="dlyogipchecker"
ROLE_NAME="dlyogipchecker-lambda-role"
API_NAME="dlyogipchecker-api"
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

# 3. Create Lambda function if not exists
if aws lambda get-function --function-name "$LAMBDA_NAME" >/dev/null 2>&1; then
  echo "☑️  Lambda function $LAMBDA_NAME already exists."
else
  LAMBDA_ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
  aws lambda create-function \
    --function-name "$LAMBDA_NAME" \
    --runtime python3.11 \
    --handler handler.lambda_handler \
    --zip-file fileb://infra/$ZIP_FILE \
    --role "$LAMBDA_ROLE_ARN" \
    --region "$REGION"
  echo "✅ Created Lambda function: $LAMBDA_NAME"
fi

# 4. (Placeholder) Setup API Gateway later
echo "📌 Skipping API Gateway setup for now. To be implemented."

echo "✅ Infrastructure setup completed."
