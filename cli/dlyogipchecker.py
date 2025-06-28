import typer
import boto3
import os
import json
from pathlib import Path
import requests

app = typer.Typer()

CONFIG_PATH = os.path.expanduser("~/.dlyogipchecker/config.json")
OUTPUT_FILE = "ip_bundle.txt"

IGNORE_DIRS = {'.git', '__pycache__', '.venv', 'node_modules'}

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)

def generate_bundle(project_path: str) -> str:
    project_root = Path(project_path).resolve()
    bundle_lines = []

    for file in project_root.rglob("*"):
        if file.is_file() and not should_ignore(file.relative_to(project_root)):
            rel_path = file.relative_to(project_root)
            bundle_lines.append(f"# {rel_path}")
            try:
                content = file.read_text(errors='ignore')
                bundle_lines.append(content)
            except Exception as e:
                bundle_lines.append(f"[Could not read file: {e}]")
            bundle_lines.append("")  # newline between files

    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(bundle_lines))

    return OUTPUT_FILE

@app.command()
def push(project_path: str):
    """
    Generate IP bundle and upload to S3
    """
    config = load_config()
    bucket = config["s3_bucket_name"]
    key = "ip_bundles/ip_bundle.txt"

    typer.echo("📦 Generating bundle...")
    output_file = generate_bundle(project_path)

    s3 = boto3.client(
    "s3",
    region_name=config.get("region_name"),
    aws_access_key_id=config.get("aws_access_key_id"),
    aws_secret_access_key=config.get("aws_secret_access_key")
)

    s3.upload_file(output_file, bucket, key)

    typer.echo(f"✅ Uploaded to S3: s3://{bucket}/{key}")

@app.command()
def trigger(to_email: str):
    """
    Trigger Lambda API to process the uploaded bundle and send email.
    """
    config = load_config()
    api_url = config.get("api_url")
    api_secret = config.get("api_secret")

    if not api_url or not api_secret:
        typer.echo("❌ Missing 'api_url' or 'api_secret' in config.")
        raise typer.Exit(1)

    headers = {
        "Content-Type": "application/json",
        "x-api-secret": api_secret
    }

    payload = {
        "to_email": to_email
    }

    typer.echo(f"📡 Triggering Lambda at: {api_url}")
    response = requests.post(api_url, headers=headers, json=payload)

    typer.echo(f"✅ Status Code: {response.status_code}")
    typer.echo(f"📨 Response: {response.text}")


if __name__ == "__main__":
    app()
