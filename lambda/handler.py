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
        logger.info("📦 Event received: %s", json.dumps(event))

        # Parse S3 event
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        logger.info(f"📥 S3 triggered: bucket={bucket}, key={key}")

        # Use default to_email from ENV (you can modify if dynamic is needed)
        to_email = os.environ.get("TO_EMAIL")
        if not to_email:
            logger.warning("❌ No TO_EMAIL env var set.")
            return {"statusCode": 200, "body": "TO_EMAIL not configured"}

        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")

        max_chunk_size = 3000
        chunks = [content[i:i + max_chunk_size] for i in range(0, len(content), max_chunk_size)]

        all_findings = []
        for idx, chunk in enumerate(chunks):
            prompt = f"Analyze the following code for potential IP issues.\n\n{chunk}"
            result = call_sonar(prompt)
            all_findings.append(f"<h3>Chunk {idx + 1}</h3><pre>{result}</pre>")

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

        return {"statusCode": 200, "body": f"✅ Report sent to {to_email}"}

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
