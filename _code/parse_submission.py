#!/usr/bin/env python3
"""
parse_submission.py
───────────────────
Parses a rendered GitHub issue form (example-submission.yml) and appends a
new entry to content/examples.yaml.

Called by the GitHub Actions workflow when an admin labels an
`example-submission` issue as `approved`.

Environment variables (set by the workflow):
    ISSUE_BODY   — raw Markdown body of the GitHub issue
    ISSUE_NUMBER — issue number (used for logging)
    ISSUE_TITLE  — issue title (fallback if title field is empty)
"""

import os
import re
import sys
import textwrap
from datetime import date
from pathlib import Path

import yaml  # PyYAML


# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_field(body: str, label: str) -> str:
    """
    Extract the text value under a GitHub issue-form heading.

    GitHub renders form fields as:
        ### Field Label
        
        value text here

    Captures everything between the heading and the next heading (or EOF).
    """
    pattern = rf"### {re.escape(label)}\s*\n+(.+?)(?=\n### |\Z)"
    match = re.search(pattern, body, re.DOTALL)
    if not match:
        return ""
    raw = match.group(1).strip()
    # GitHub uses "_No response_" when a field is left blank
    if raw.lower() in ("_no response_", "none", "n/a", ""):
        return ""
    return re.sub(r"\s+", " ", raw).strip()


def extract_checkboxes(body: str, label: str) -> list[str]:
    """
    Return a list of checked checkbox labels under a given heading.

    GitHub renders checked boxes as:  - [x] Label text
    """
    section_pat = rf"### {re.escape(label)}\s*\n+(.*?)(?=\n### |\Z)"
    m = re.search(section_pat, body, re.DOTALL)
    if not m:
        return []
    return [
        item.strip()
        for item in re.findall(r"- \[x\] (.+)", m.group(1), re.IGNORECASE)
    ]


def slugify(text: str) -> str:
    """Simple filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def next_id(examples: list[dict]) -> int:
    """Return max existing id + 1, or 1 if the list is empty."""
    ids = [int(ex.get("id", 0)) for ex in examples if ex.get("id")]
    return max(ids, default=0) + 1


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    body        = os.environ.get("ISSUE_BODY", "").strip()
    issue_num   = os.environ.get("ISSUE_NUMBER", "?")
    issue_title = os.environ.get("ISSUE_TITLE", "").strip()

    if not body:
        print("ERROR: ISSUE_BODY is empty — nothing to parse.", file=sys.stderr)
        sys.exit(1)

    print(f"\n── Parsing issue #{issue_num} ──────────────────────────────────")

    # ── Extract form fields ──────────────────────────────────────────────────
    title       = extract_field(body, "Short Title") or issue_title
    description = extract_field(body, "Short Description")
    url         = extract_field(body, "URL / Link")
    author      = extract_field(body, "Author / Organisation")
    image_url   = extract_field(body, "Screenshot or Logo URL")
    notes       = extract_field(body, "Additional Notes (optional)")

    # Tools
    tools_checked = extract_checkboxes(body, "Tool Type(s)")
    tools_new_raw = extract_field(body, "New Tool Type(s) — not in the list above?")
    tools_new     = [t.strip() for t in tools_new_raw.split(",") if t.strip()]
    all_tools     = tools_checked + tools_new

    # Keywords
    kw_checked   = extract_checkboxes(body, "Keyword(s)")
    kw_new_raw   = extract_field(body, "New Keyword(s) — not in the list above?")
    kw_new       = [k.strip() for k in kw_new_raw.split(",") if k.strip()]
    all_keywords = kw_checked + kw_new

    # ── Validation ───────────────────────────────────────────────────────────
    errors = []
    if not title:
        errors.append("title is empty")
    if not description:
        errors.append("description is empty")
    if not url:
        errors.append("url is empty")
    if errors:
        print(f"ERROR: Required fields missing — {', '.join(errors)}", file=sys.stderr)
        sys.exit(1)

    # ── Load existing YAML ────────────────────────────────────────────────────
    yaml_path = Path("_code/examples.yaml")
    if not yaml_path.exists():
        print(f"ERROR: {yaml_path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    examples: list[dict] = data.get("examples", [])

    # ── Image filename ────────────────────────────────────────────────────────
    # If a URL was provided we record the intended local filename.
    # The GitHub Action PR description reminds admins to download it manually.
    if image_url:
        image_filename = slugify(title) + ".png"
        print(f"\n  ⚠️  Image URL provided: {image_url}")
        print(f"     Admin must download → content/card-images/{image_filename}")
    else:
        image_filename = ""

    # ── Build new entry ───────────────────────────────────────────────────────
    new_entry: dict = {
        "id":          next_id(examples),
        "title":       title,
        "description": description,
        "url":         url,
        "tools":       all_tools if all_tools else [],
        "keywords":    all_keywords if all_keywords else [],
        "image":       image_filename,
        "author":      author,
        "date_added":  date.today().isoformat(),
    }
    if notes:
        new_entry["notes"] = notes  # stored for admin reference; not shown on card

    print("\n  New entry:")
    for k, v in new_entry.items():
        print(f"    {k}: {v}")

    # ── Append and write ──────────────────────────────────────────────────────
    examples.append(new_entry)
    data["examples"] = examples

    # Preserve the header comment block from the original file
    with open(yaml_path, encoding="utf-8") as f:
        original = f.read()

    # Extract the leading comment (everything before the first non-comment line
    # that starts a YAML mapping/sequence, i.e. before "examples:")
    comment_block = ""
    for line in original.splitlines(keepends=True):
        if line.startswith("#") or line.strip() == "" or line.startswith("---"):
            comment_block += line
        else:
            break  # stop at "examples:"

    # Serialise the updated data
    new_yaml = yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        indent=2,
        width=88,
    )

    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(comment_block)
        f.write(new_yaml)

    print(f"\n✅  Appended entry id={new_entry['id']} to {yaml_path}")
    print("    Commit this file (and any downloaded image) to complete the PR.\n")


if __name__ == "__main__":
    main()
