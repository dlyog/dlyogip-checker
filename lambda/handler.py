import os

def lambda_handler(event, context):
    secret = os.environ.get("API_SECRET_KEY")
    headers = event.get("headers", {})
    client_secret = headers.get("x-api-secret")

    if client_secret != secret:
        return {
            "statusCode": 401,
            "body": "Unauthorized"
        }

    return {
        "statusCode": 200,
        "body": "Valid Request"
    }
