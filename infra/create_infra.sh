#!/bin/bash
set -e

# Configurable values
REGION="us-west-2"
BUCKET_NAME="dlyogipchecker-bucket"
ROLE_NAME="dlyogipchecker-lambda-role"
LAMBDA_NAME="dlyogipchecker"
ZIP_FILE="lambda.zip"
S3_POLICY_NAME="DLyogipcheckerFullS3AccessPolicy"

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
  echo "✅ Created IAM role: $ROLE_NAME"
else
  echo "☑️  IAM Role $ROLE_NAME already exists."
fi

# 3. Attach AWSLambdaBasicExecutionRole managed policy
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
echo "🔗 Attached AWSLambdaBasicExecutionRole to $ROLE_NAME"

# 4. Create and attach custom inline policy for full S3 access
INLINE_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowFullS3AccessForDLyogIPChecker",
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::${BUCKET_NAME}",
        "arn:aws:s3:::${BUCKET_NAME}/*"
      ]
    }
  ]
}
EOF
)

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "$S3_POLICY_NAME" \
  --policy-document "$INLINE_POLICY"

echo "✅ Attached inline policy $S3_POLICY_NAME to $ROLE_NAME for full S3 access."

echo "✅ Infrastructure setup complete."
