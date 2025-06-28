import os
import smtplib
import json
from email.message import EmailMessage

def send_email(to_email):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    msg = EmailMessage()
    msg["Subject"] = "DLyog IP Checker Notification"
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content("Hello,\n\nYour submission has been received and is being processed.\n\n— DLyog IPChecker")

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

def lambda_handler(event, context):
    secret = os.environ.get("API_SECRET_KEY")
    headers = event.get("headers", {})
    client_secret = headers.get("x-api-secret")

    if client_secret != secret:
        return {
            "statusCode": 401,
            "body": "Unauthorized"
        }

    try:
        body = json.loads(event.get("body") or "{}")
        to_email = body.get("to_email")

        if not to_email:
            return {
                "statusCode": 400,
                "body": "Missing 'to_email' in request body."
            }

        send_email(to_email)

        return {
            "statusCode": 200,
            "body": f"Email sent to {to_email}"
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }
