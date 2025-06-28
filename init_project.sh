#!/bin/bash

set -e

echo "Creating directory structure..."

mkdir -p infra
mkdir -p lambda
mkdir -p cli
mkdir -p .github/workflows

touch infra/{deploy.sh,README.md}
touch lambda/{handler.py,README.md}
touch cli/{dlyogipchecker.py,fetch_config.py,__init__.py}
touch .github/workflows/deploy.yml

# Sample README and config file
cat > README.md <<EOF
# dlyogip-checker

This project is built for the AWS Lambda Hackathon by **DLYog Lab Research Services LLC**.

## Overview

A CLI tool that allows secure code submission to a Lambda backend for analysis. Judges or users upload code via CLI, which triggers a Lambda function to analyze the content and return results.

## Components

- AWS Lambda (core compute)
- API Gateway (Lambda trigger)
- S3 (config storage)
- CLI (`dlyogipchecker`)
- GitHub Action (deploys infra + Lambda + config)

EOF

cat > config-template.json <<EOF
{
  "api_url": "https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/check",
  "api_key": "replace-with-your-api-key"
}
EOF

echo "✅ Project structure created."
#!/bin/bash

set -e

echo "Creating directory structure..."

mkdir -p infra
mkdir -p lambda
mkdir -p cli
mkdir -p .github/workflows

touch infra/{deploy.sh,README.md}
touch lambda/{handler.py,README.md}
touch cli/{dlyogipchecker.py,fetch_config.py,__init__.py}
touch .github/workflows/deploy.yml

# Sample README and config file
cat > README.md <<EOF
# dlyogip-checker

This project is built for the AWS Lambda Hackathon by **DLYog Lab Research Services LLC**.

## Overview

A CLI tool that allows secure code submission to a Lambda backend for analysis. Judges or users upload code via CLI, which triggers a Lambda function to analyze the content and return results.

## Components

- AWS Lambda (core compute)
- API Gateway (Lambda trigger)
- S3 (config storage)
- CLI (`dlyogipchecker`)
- GitHub Action (deploys infra + Lambda + config)

EOF

cat > config-template.json <<EOF
{
  "api_url": "https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/check",
  "api_key": "replace-with-your-api-key"
}
EOF

echo "✅ Project structure created."
