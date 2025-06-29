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

    try:
        logger.info("🌐 Calling Perplexity API with timeout...")
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=data,
            timeout=180  # seconds
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.Timeout:
        logger.error("⏱️ Perplexity API request timed out.")
        raise
    except requests.RequestException as e:
        logger.error("❌ Perplexity API request failed: %s", str(e))
        raise


def format_html_report(json_text):
    try:
        data = json.loads(json_text)
    except Exception:
        logger.warning("⚠️ Failed to parse JSON from Sonar. Returning raw content.")
        return f"<pre>{json_text}</pre>"

    html = "<div>"
    if "summary" in data:
        html += f"<h2>🔍 Summary</h2><p>{data['summary']}</p>"

    if "validation" in data and isinstance(data["validation"], dict):
        html += "<h2>📋 Validation Results</h2><ul>"
        for key, val in data["validation"].items():
            html += f"<li><strong>{key}:</strong> "
            if isinstance(val, dict):
                html += "<ul>"
                for subkey, subval in val.items():
                    html += f"<li>{subkey}: {subval}</li>"
                html += "</ul>"
            else:
                html += f"{val}"
            html += "</li>"
        html += "</ul>"

    if "verdict" in data:
        html += f"<h2>✅ Verdict</h2><p><strong>{data['verdict']}</strong></p>"

    html += "</div>"
    return html


def lambda_handler(event, context):
    try:
        logger.info("📦 Event received: %s", json.dumps(event))

        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        logger.info(f"📥 S3 triggered: bucket={bucket}, key={key}")

        to_email = os.environ.get("TO_EMAIL")
        if not to_email:
            logger.warning("❌ No TO_EMAIL env var set.")
            return {"statusCode": 200, "body": "TO_EMAIL not configured"}

        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")

        max_chunk_size = 3000
        chunks = [content[i:i + max_chunk_size] for i in range(0, len(content), max_chunk_size)]

        if not chunks:
            logger.warning("⚠️ Empty bundle content.")
            return {"statusCode": 200, "body": "Empty bundle."}

        prompt = f"Analyze the following code for potential copyright, patent, or trademark issues. Provide summary and details in JSON format.\n\n{chunks[0]}"
        logger.info("🔍 Prompt sent to Sonar:\n%s", prompt)

        result = call_sonar(prompt)
        logger.info("🧠 Sonar response (raw):\n%s", result)

        formatted_html = format_html_report(result)

        final_report = f"""
        <html>
        <head><style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            h1 {{ color: #333; }}
            h2 {{ margin-top: 24px; color: #2a4d7f; }}
            ul {{ margin-left: 20px; }}
            footer {{ margin-top: 40px; font-size: 0.9em; color: #888; }}
        </style></head>
        <body>
        <h1>DLyog IP Checker Report</h1>
        {formatted_html}
        <footer>
  <p>© 2025 DLyog Lab</p>
  <p style="margin-top:20px; font-size:0.9em; color:#666;">
    <strong>Disclaimer:</strong> This analysis is part of an AI experiment and may contain inaccuracies.
    For professional advice on intellectual property including patents, trademarks, or copyrights,
    always consult a qualified IP attorney.
  </p>
</footer>

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
        <footer>
  <p>© 2025 DLyog Lab</p>
  <p style="margin-top:20px; font-size:0.9em; color:#666;">
    <strong>Disclaimer:</strong> This analysis is part of an AI experiment and may contain inaccuracies.
    For professional advice on intellectual property including patents, trademarks, or copyrights,
    always consult a qualified IP attorney.
  </p>
</footer>

        </body>
        </html>
        """

        try:
            to_email = os.environ.get("TO_EMAIL")
            if to_email:
                logger.info("📧 Sending error report email")
                send_email(to_email, "DLyog IP Check Error Report", fallback_body)
        except Exception as inner:
            logger.error("🚨 Failed to send fallback email: %s", str(inner))

        return {
            "statusCode": 200,
            "body": "⚠️ An error occurred. If email was provided, an error report has been sent."
        }
