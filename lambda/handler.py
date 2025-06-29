"""
DLyog IP Checker – Lambda
Triggered by an S3 `ip_bundle.zip` upload.
• Downloads ZIP to /tmp
• Reads up to 10 files
• Calls Perplexity (Sonar) once per file
• Aggregates results into a styled HTML report
• Emails the report
"""

import io
import json
import logging
import os
import smtplib
import traceback
import zipfile
from email.message import EmailMessage
from typing import List, Tuple

import boto3
import requests

# ---------------------------  Logging  ------------------------------------ #
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --------------------------  E-mail helper  -------------------------------- #
def send_email(to_email: str, subject: str, html_body: str) -> None:
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content("HTML report attached.", subtype="plain")
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


# --------------------------  Sonar (Perplexity)  --------------------------- #
def call_sonar(prompt: str, timeout: int = 180) -> str:
    api_key = os.environ["PERPLEXITY_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an IP rights analyst. "
                    "Return a JSON with summary, validation, and verdict."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }

    logger.info("🌐  Calling Perplexity Sonar …")
    resp = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# -------------------------  HTML formatting  ------------------------------ #
def format_html_report(json_text: str) -> str:
    """
    Convert Sonar's JSON (or plain text fallback) to a stylised HTML snippet.
    """
    try:
        data = json.loads(json_text)
    except Exception:
        # Not JSON?  Wrap raw text.
        return f"<pre>{json_text}</pre>"

    html = ["<div>"]

    if "summary" in data:
        html.append(f"<h3>🔍 Summary</h3><p>{data['summary']}</p>")

    if "validation" in data and isinstance(data["validation"], dict):
        html.append("<h4>📋 Validation</h4><ul>")
        for k, v in data["validation"].items():
            if isinstance(v, dict):
                html.append(f"<li><strong>{k}</strong><ul>")
                for sk, sv in v.items():
                    html.append(f"<li>{sk}: {sv}</li>")
                html.append("</ul></li>")
            else:
                html.append(f"<li><strong>{k}</strong>: {v}</li>")
        html.append("</ul>")

    if "verdict" in data:
        html.append(f"<p><strong>Verdict:</strong> {data['verdict']}</p>")

    html.append("</div>")
    return "".join(html)


# -----------------------------  Lambda  ----------------------------------- #
MAX_FILES = 10               # hard upper bound per ZIP
MAX_FILE_CHARS = 3500        # truncate huge files before sending
SONAR_TIMEOUT = 180          # seconds – keep ≤ API hard limit


def extract_zip(content: bytes) -> List[Tuple[str, str]]:
    """
    Return list of (filename, text) tuples for up to MAX_FILES members inside
    the uploaded ZIP.
    """
    texts: List[Tuple[str, str]] = []
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        members = z.infolist()[:MAX_FILES]
        for m in members:
            if m.is_dir():
                continue
            with z.open(m) as fh:
                raw = fh.read().decode("utf-8", errors="ignore")
                texts.append((m.filename, raw[:MAX_FILE_CHARS]))
    return texts


def lambda_handler(event, context):
    try:
        # 1. Event info
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        logger.info("📥  New object:  s3://%s/%s", bucket, key)

        # 2. Who to mail?
        to_email = os.environ.get("TO_EMAIL")
        if not to_email:
            logger.warning("❌  TO_EMAIL env var not set.")
            return {"statusCode": 200, "body": "Email not configured."}

        # 3. Download ZIP
        s3 = boto3.client("s3")
        obj = s3.get_object(Bucket=bucket, Key=key)
        zip_bytes = obj["Body"].read()

        # 4. Extract files
        files = extract_zip(zip_bytes)
        if not files:
            logger.warning("⚠️  ZIP had no readable files.")
            return {"statusCode": 200, "body": "Empty ZIP."}

        # 5. Analyse each file in turn
        sections = []
        for fname, text in files:
            prompt = (
                "Analyze the following file for potential copyright, "
                "patent, or trademark issues. Return JSON with summary, "
                "validation, and verdict.\n\n"
                f"### File: {fname}\n\n{text}"
            )

            # Bail early if time is running out
            if context.get_remaining_time_in_millis() < 60000:   # < 60 s left
                sections.append(
                    f"<h2>{fname}</h2><p><em>Skipped – Lambda about to time-out.</em></p>"
                )
                break

            try:
                raw_json = call_sonar(prompt, timeout=SONAR_TIMEOUT)
                html_snip = format_html_report(raw_json)
            except Exception as e:
                logger.error("❌  Sonar failed on %s: %s", fname, e)
                html_snip = f"<p><strong>Error analysing {fname}:</strong> {e}</p>"

            sections.append(f"<h2>{fname}</h2>{html_snip}")

        # 6. Assemble final HTML (✨ fancy styling here)
        report_body = "\n".join(sections)
        final_html = f"""
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <title>DLyog IP Checker Report</title>
          <style>
            body {{
              margin: 0;
              padding: 40px 0;
              background: #f5f7fa;
              font-family: Arial, Helvetica, sans-serif;
              line-height: 1.6;
              color: #333;
            }}
            .card {{
              max-width: 900px;
              margin: 0 auto;
              background: #ffffff;
              border: 1px solid #e0e4e8;
              border-radius: 12px;
              box-shadow: 0 4px 12px rgba(0,0,0,.05);
              overflow: hidden;
            }}
            header {{
              background: linear-gradient(135deg, #2a4d7f 0%, #4268a2 100%);
              color: #fff;
              padding: 24px 32px;
            }}
            header h1 {{
              margin: 0;
              font-size: 1.75rem;
              letter-spacing: .5px;
            }}
            main {{
              padding: 32px;
            }}
            h2 {{
              margin-top: 1.6em;
              font-size: 1.25rem;
              color: #2a4d7f;
              border-bottom: 1px solid #e0e4e8;
              padding-bottom: 4px;
            }}
            h3 {{ margin-top: 1.2em; }}
            h4 {{ margin: 1em 0 .6em; font-size: 1rem; }}
            ul {{ margin-left: 1.2em; }}
            footer {{
              border-top: 1px solid #e0e4e8;
              background: #fafbfc;
              padding: 24px 32px;
              font-size: 0.85rem;
              color: #666;
            }}
            footer p {{ margin: 0 0 8px; }}
          </style>
        </head>
        <body>
          <div class="card">
            <header>
              <h1>DLyog IP Checker Report</h1>
            </header>
            <main>
              {report_body}
            </main>
            <footer>
              <p>© 2025 DLyog Lab</p>
              <p><strong>Disclaimer:</strong> This analysis is part of an AI experiment and may contain inaccuracies.
              For professional advice on intellectual property, always consult a qualified IP attorney.</p>
            </footer>
          </div>
        </body>
        </html>
        """

        # 7. Send
        send_email(to_email, "DLyog IP Check Report", final_html)
        logger.info("📧  Report emailed to %s", to_email)
        return {"statusCode": 200, "body": "Report sent."}

    except Exception as exc:
        logger.error("Unhandled Lambda error:\n%s", traceback.format_exc())
        # Best-effort failure mail
        try:
            if os.environ.get("TO_EMAIL"):
                send_email(
                    os.environ["TO_EMAIL"],
                    "DLyog IP Check – Error",
                    f"<pre>{traceback.format_exc()}</pre>",
                )
        finally:
            return {"statusCode": 500, "body": f"Error: {exc}"}
