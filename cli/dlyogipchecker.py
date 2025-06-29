#!/usr/bin/env python3
"""
DLyog IP Checker – CLI uploader
• Scans a project directory.
• Picks up to 10 relevant source files (by most-recent mtime).
• Writes them into a ZIP archive   ip_bundle.zip
• Uploads to the configured S3 bucket/key.
"""

import os
import json
import zipfile
from pathlib import Path
from typing import List

import boto3
import typer

app = typer.Typer()

CONFIG_PATH = os.path.expanduser("~/.dlyogipchecker/config.json")
OUTPUT_ZIP = "ip_bundle.zip"

# Directories and patterns to skip outright
IGNORE_DIRS = {".git", "__pycache__", ".venv", "node_modules"}

# Extensions worth analysing – adjust if needed
ALLOWED_EXTENSIONS = {".py", ".md", ".txt", ".js", ".ts", ".java", ".rb", ".go"}


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def should_ignore(path: Path) -> bool:
    """Return True if any component of `path` is in IGNORE_DIRS."""
    return any(part in IGNORE_DIRS for part in path.parts)


def select_files(project_root: Path, limit: int = 10) -> List[Path]:
    """
    Return up to `limit` files under project_root that:
      • are regular files
      • are NOT in ignored directories
      • have an allowed extension
    The list is ordered by last-modified time (newest first).
    """
    candidates = [
        f
        for f in project_root.rglob("*")
        if (
            f.is_file()
            and not should_ignore(f.relative_to(project_root))
            and f.suffix.lower() in ALLOWED_EXTENSIONS
        )
    ]
    # Sort newest → oldest and trim
    candidates.sort(key=lambda fp: fp.stat().st_mtime, reverse=True)
    return candidates[:limit]


def generate_zip(project_path: str) -> str:
    """
    Build OUTPUT_ZIP containing the chosen files.
    Each entry keeps its relative path so the Lambda can show filenames.
    """
    project_root = Path(project_path).resolve()
    chosen = select_files(project_root)

    if not chosen:
        raise RuntimeError("No suitable files found to bundle.")

    with zipfile.ZipFile(OUTPUT_ZIP, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in chosen:
            arcname = file_path.relative_to(project_root)
            zf.write(file_path, arcname=str(arcname))

    return OUTPUT_ZIP


# --------------------------------------------------------------------------- #
# CLI command
# --------------------------------------------------------------------------- #
@app.command()
def push(project_path: str):
    """
    Bundle up to 10 source files and upload to S3.
    """
    config = load_config()
    bucket = config["s3_bucket_name"]
    key = "ip_bundles/ip_bundle.zip"

    typer.echo("📦  Building ZIP bundle …")
    archive = generate_zip(project_path)

    s3 = boto3.client(
        "s3",
        region_name=config.get("region_name"),
        aws_access_key_id=config.get("aws_access_key_id"),
        aws_secret_access_key=config.get("aws_secret_access_key"),
    )
    s3.upload_file(archive, bucket, key)

    typer.echo(f"✅  Uploaded to s3://{bucket}/{key}")
    typer.echo("🚀  Lambda will be triggered automatically.")


if __name__ == "__main__":
    app()
