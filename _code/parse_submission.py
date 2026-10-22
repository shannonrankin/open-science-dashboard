#!/usr/bin/env python3
"""Add an approved example submission and any supplied image to dashboard data."""

import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import yaml

EXAMPLES_PATH = Path("content/examples.yaml")
TAXONOMY_PATH = Path("content/tools_and_keywords.yml")
IMAGE_DIR = Path("content/card-images")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def extract_field(body: str, label: str) -> str:
    match = re.search(
        rf"### {re.escape(label)}\s*\n+(.+?)(?=\n### |\Z)", body, re.DOTALL
    )
    if not match:
        return ""
    value = match.group(1).strip()
    return "" if value.lower() in {"_no response_", "none", "n/a", ""} else value


def extract_checkboxes(body: str, label: str) -> list[str]:
    section = extract_field(body, label)
    return [
        value.strip()
        for value in re.findall(r"^- \[x\] (.+)$", section, re.MULTILINE | re.IGNORECASE)
    ]


def split_suggestions(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,;\n]+", value) if item.strip()]


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "example"


def extract_image_url(body: str, submitted_url: str) -> str:
    if submitted_url.startswith(("https://", "http://")):
        return submitted_url
    matches = re.findall(r"https?://[^\s)>]+", body)
    for url in matches:
        host = urllib.parse.urlparse(url).hostname or ""
        if host == "user-images.githubusercontent.com" or host == "github.com":
            return url.rstrip(".,")
    return ""


def download_image(url: str, title: str) -> str:
    if not url.startswith(("https://", "http://")):
        return ""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "open-science-dashboard"})
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get_content_type().lower()
            extension = IMAGE_EXTENSIONS.get(content_type)
            if extension is None:
                return ""
            payload = response.read(MAX_IMAGE_BYTES + 1)
        if not payload or len(payload) > MAX_IMAGE_BYTES:
            return ""
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{slugify(title)}{extension}"
        (IMAGE_DIR / filename).write_bytes(payload)
        return filename
    except (OSError, ValueError, urllib.error.URLError):
        return ""


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def main() -> None:
    body = os.environ.get("ISSUE_BODY", "").strip()
    issue_title = os.environ.get("ISSUE_TITLE", "").strip()
    if not body:
        sys.exit("ERROR: ISSUE_BODY is empty.")

    title = extract_field(body, "Short Title") or issue_title
    description = extract_field(body, "Short Description")
    url = extract_field(body, "URL / Link")
    author = extract_field(body, "Author / Organisation")
    if not all((title, description, url)):
        sys.exit("ERROR: title, description, and URL / Link are required.")

    tools = unique(
        extract_checkboxes(body, "Tool Type(s)")
        + split_suggestions(extract_field(body, "Suggested New Tools (if not listed above)"))
    )
    keywords = unique(
        extract_checkboxes(body, "Keyword(s)")
        + split_suggestions(extract_field(body, "Suggested New Keywords (if not listed above)"))
    )
    examples_data = load_yaml(EXAMPLES_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    examples = examples_data.setdefault("examples", [])
    image_url = extract_image_url(body, extract_field(body, "Screenshot or Logo URL"))
    image = download_image(image_url, title) if image_url else ""

    examples.append(
        {
            "id": max((int(item.get("id", 0)) for item in examples), default=0) + 1,
            "title": title,
            "description": re.sub(r"\s+", " ", description),
            "url": url,
            "tools": tools,
            "keywords": keywords,
            "image": image,
            "author": author,
            "date_added": date.today().isoformat(),
        }
    )
    taxonomy["tools"] = unique(list(taxonomy.get("tools", [])) + tools)
    taxonomy["keywords"] = unique(list(taxonomy.get("keywords", [])) + keywords)

    EXAMPLES_PATH.write_text(
        yaml.safe_dump(examples_data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    TAXONOMY_PATH.write_text(
        yaml.safe_dump(taxonomy, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    print(f"Added example {title!r}; image: {image or 'placeholder'}")


if __name__ == "__main__":
    main()
