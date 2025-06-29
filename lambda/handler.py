import os
import smtplib
import json
import boto3
import logging
import traceback
from email.message import EmailMessage
import requests

# Set up logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
            {
                "role": "system",
                "content": "You are an IP rights analyst. Return a JSON with summary and detailed validation.",
            },
            {"role": "user", "content": prompt},
        ]
    }
    response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(f"Sonar API failed with status code {response.status_code}: {response.text}")
    return response.json()["choices"][0]["message"]["content"].strip()


def lambda_handler(event, context):
    try:
        logger.info("🔐 Validating API secret")
        secret = os.environ.get("API_SECRET_KEY")
        headers = event.get("headers", {})
        client_secret = headers.get("x-api-secret")

        if client_secret != secret:
            return {
                "statusCode": 200,
                "body": "Unauthorized: Invalid API secret"
            }

        logger.info("📨 Parsing input body")
        body = json.loads(event.get("body") or "{}")
        to_email = body.get("to_email")

        if not to_email:
            return {
                "statusCode": 200,
                "body": "Missing 'to_email' in request body."
            }

        logger.info("📥 Fetching bundle from S3")
        s3 = boto3.client("s3")
        bucket = os.environ.get("S3_BUCKET", "dlyogipchecker-bucket")
        key = "ip_bundles/ip_bundle.txt"
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")

        logger.info(f"📄 Loaded {len(content)} characters from bundle")
        max_chunk_size = 3000
        chunks = [content[i:i + max_chunk_size] for i in range(0, len(content), max_chunk_size)]
        logger.info(f"🔍 Split content into {len(chunks)} chunks")

        all_findings = []
        for idx, chunk in enumerate(chunks):
            logger.info(f"⚙️ Analyzing chunk {idx + 1}/{len(chunks)}")
            prompt = f"Analyze the following code for potential copyright, patent, or trademark issues. Provide summary and details in JSON format.\n\n{chunk}"
            result = call_sonar(prompt)
            all_findings.append(f"<h3>Chunk {idx + 1}</h3><pre>{result}</pre>")

        logger.info("✅ Sonar analysis complete. Building HTML report.")
        final_report = f"""
        <html>
        <head><style>body {{ font-family: Arial; }}</style></head>
        <body>
        <h1>DLyog IP Checker Report</h1>
        {''.join(all_findings)}
        <footer><p style='margin-top:40px;'>© 2025 DLyog</p></footer>
        </body>
        </html>
        """

        logger.info("📧 Sending report email")
        send_email(to_email, "DLyog IP Check Report", final_report)

        return {
            "statusCode": 200,
            "body": f"✅ Report sent to {to_email}"
        }

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error("❌ Lambda error:\n%s", error_trace)

        fallback_body = f"""
        <html>
        <body>
        <h2>❌ Error in DLyog Lambda Execution</h2>
        <pre>{error_trace}</pre>
        <footer><p style='margin-top:40px;'>© 2025 DLyog</p></footer>
        </body>
        </html>
        """

        try:
            body = json.loads(event.get("body") or "{}")
            to_email = body.get("to_email")
            if to_email:
                logger.info("📧 Sending error report email")
                send_email(to_email, "DLyog IP Check Error Report", fallback_body)
        except Exception as inner:
            logger.error("🚨 Failed to send fallback email: %s", str(inner))

        return {
            "statusCode": 200,
            "body": "⚠️ An error occurred. If email was provided, an error report has been sent."
        }
