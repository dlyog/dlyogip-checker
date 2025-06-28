#!/bin/bash
set -e

REGION="us-west-2"
BUCKET_NAME="dlyogipchecker-bucket"
ZIP_FILE="lambda.zip"
LAMBDA_NAME="dlyogipchecker"

echo "📦 Zipping Lambda function..."
cd lambda
zip -r9 "../infra/$ZIP_FILE" handler.py > /dev/null
cd ..

echo "☁️ Uploading $ZIP_FILE to S3..."
aws s3 cp "infra/$ZIP_FILE" "s3://$BUCKET_NAME/$ZIP_FILE" --region "$REGION"

echo "🚀 Updating Lambda function code..."
aws lambda update-function-code \
  --function-name "$LAMBDA_NAME" \
  --s3-bucket "$BUCKET_NAME" \
  --s3-key "$ZIP_FILE" \
  --region "$REGION"

echo "✅ Lambda function deployed."
