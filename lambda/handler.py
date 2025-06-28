import os
import smtplib
import json
import boto3
from email.message import EmailMessage
import urllib.parse
import requests

def send_email(to_email, subject, html_body):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content("This is an HTML email.", subtype="plain")
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

def call_sonar(prompt):
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "You are an IP rights analyst. Return a JSON with summary and detailed validation."},
            {"role": "user", "content": prompt},
        ]
    }
    response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data)
    if response.status_code != 200:
        raise Exception("Sonar API failed")
    content = response.json()["choices"][0]["message"]["content"].strip()
    return content

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

        s3 = boto3.client("s3")
        bucket = os.environ.get("S3_BUCKET", "DLYog Labipchecker-bucket")
        key = "ip_bundles/ip_bundle.txt"
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")

        max_chunk_size = 3000
        chunks = [content[i:i+max_chunk_size] for i in range(0, len(content), max_chunk_size)]

        all_findings = []
        for idx, chunk in enumerate(chunks):
            prompt = f"Analyze the following code for potential copyright, patent, or trademark issues. Provide summary and details in JSON format.\n\n{chunk}"
            result = call_sonar(prompt)
            all_findings.append(f"<h3>Chunk {idx+1}</h3><pre>{result}</pre>")

        final_report = f"""
        <html>
        <head><style>body {{ font-family: Arial; }}</style></head>
        <body>
        <h1>DLYog Lab IP Checker Report</h1>
        {''.join(all_findings)}
        <footer><p style='margin-top:40px;'>© 2025 DLYog Lab Lab</p></footer>
        </body>
        </html>
        """

        send_email(to_email, "DLYog Lab IP Check Report", final_report)

        return {
            "statusCode": 200,
            "body": f"Report sent to {to_email}"
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }
