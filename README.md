# dlyogip-checker

This project is built for the AWS Lambda Hackathon by **DLYog Lab Research Services LLC**.

## Overview

A CLI tool that allows secure code submission to a Lambda backend for analysis. Judges or users upload code via CLI, which triggers a Lambda function to analyze the content and return results.

## Components

- AWS Lambda (core compute)
- API Gateway (Lambda trigger)
- S3 (config storage)
- CLI ()
- GitHub Action (deploys infra + Lambda + config)

