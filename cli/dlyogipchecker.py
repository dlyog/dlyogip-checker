# cli/dlyogipchecker.py

import typer
import boto3
import os
import json
from pathlib import Path

app = typer.Typer()

CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config():
    if not CONFIG_PATH.exists():
        typer.secho("❌ Config file not found. Please download config.json.", fg=typer.colors.RED)
        raise typer.Exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)

@app.command()
def upload(path: str):
    """
    Upload a file to S3 bucket defined in config.
    """
    config = load_config()
    bucket = config["s3_bucket"]
    key = os.path.basename(path)

    s3 = boto3.client("s3", region_name=config["region"])
    s3.upload_file(path, bucket, key)

    typer.secho(f"✅ Uploaded {path} to s3://{bucket}/{key}", fg=typer.colors.GREEN)

@app.command()
def check():
    """
    Call the Lambda HTTP endpoint and print result.
    """
    config = load_config()
    import requests
    response = requests.get(config["lambda_api_url"])
    
    if response.ok:
        typer.secho("✅ Lambda Response:", fg=typer.colors.GREEN)
        typer.echo(response.text)
    else:
        typer.secho(f"❌ Failed: {response.status_code}", fg=typer.colors.RED)

if __name__ == "__main__":
    app()
