#!/usr/bin/env python3
"""
memory-consistency-auditor: local structured scan of Claude memory markdown files.

Produces a metadata-only JSON report. No file content is exposed in the output.
Supports file code system (File A, File B, ...) to anonymize filenames.

Usage:
    python scripts/audit_memory.py --json
    python scripts/audit_memory.py --memory-dir /custom/path --max-files 10 --json
    python scripts/audit_memory.py --include-filenames --json
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MEMORY_DIR = os.path.expanduser(
    "~/.claude/projects/-Users-sakura/memory"
)
DEFAULT_MAX_FILES = 6
FILE_CODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SENSITIVE_PATTERNS: list[str] = [
    r"(?i)(api[_-]?key|secret|password|token|credential)[\s=:]*['\"]?[A-Za-z0-9_\-\.]{8,}",
    r"(?i)sk-[A-Za-z0-9]{20,}",
    r"(?i)AIza[0-9A-Za9\-_]{35}",
]
MAX_HEADINGS_SAMPLE = 8
MAX_HEADING_LENGTH = 80
LARGE_FILE_THRESHOLD = 50 * 1024  # 50 KB

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def path_hash(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]


def file_code(index: int) -> str:
    if index < len(FILE_CODE_ALPHABET):
        return f"File {FILE_CODE_ALPHABET[index]}"
    return f"File_{index}"


def truncate(s: str, max_len: int = MAX_HEADING_LENGTH) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def extract_frontmatter(text: str) -> tuple[dict[str, str], int]:
    """Returns (frontmatter_dict, line_number_of_end_of_frontmatter).
    If no frontmatter found, returns ({}, 0)."""
    if not text.startswith("---"):
        return {}, 0
    end_idx = text.find("---", 3)
    if end_idx == -1:
        return {}, 0
    block = text[3:end_idx].strip()
    fm: dict[str, str] = {}
    for line in block.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    # Count lines consumed (including opening and closing ---)
    lines_consumed = 2 + block.count("\n")
    return fm, lines_consumed


def extract_headings(text: str, body_start: int) -> list[str]:
    """Extract heading lines after the frontmatter."""
    body = text[body_start:]
    headings = re.findall(r"^(#{1,6})\s+(.+)$", body, re.MULTILINE)
    result = []
    for hashes, title in headings:
        level = len(hashes)
        result.append(f"h{level}:{truncate(title.strip())}")
    return result


def extract_links(text: str) -> tuple[int, int]:
    md_links = len(re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text))
    wiki_links = len(re.findall(r"\[\[([^\]]+)\]\]", text))
    return md_links, wiki_links


def check_sensitive(text: str, filename: str) -> list[str]:
    """Check for sensitive content patterns.
    Returns list of issue descriptions (without revealing the match).
    """
    issues = []
    for pattern in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            # Count unique lines where matches occur to estimate scope
            lines_matched = set()
            for m in re.finditer(pattern, text):
                line_num = text[: m.start()].count("\n") + 1
                lines_matched.add(line_num)
            issues.append(
                f"Sensitive pattern detected in {filename}: "
                f"matched '{pattern}' on {len(lines_matched)} line(s)"
            )
    return issues


def check_heading_hierarchy(headings: list[str]) -> list[str]:
    """Check heading level skipping."""
    issues = []
    levels = []
    for h in headings:
        m = re.match(r"^h(\d+):", h)
        if m:
            levels.append(int(m.group(1)))
    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            issues.append(
                f"Heading level skip: h{levels[i-1]} → h{levels[i]} "
                f"(line ~{i + 1})"
            )
    return issues


# ---------------------------------------------------------------------------
# Main audit logic
# ---------------------------------------------------------------------------


def audit_directory(
    memory_dir: str,
    max_files: int = DEFAULT_MAX_FILES,
    include_filenames: bool = False,
) -> dict:
    result: dict = {
        "mode": "strict_local_audit",
        "scope": memory_dir,
        "file_count": 0,
        "stopped": False,
        "stop_reason": None,
        "files": [],
        "global_issues": [],
    }

    path = Path(memory_dir)
    if not path.is_dir():
        result["stopped"] = True
        result["stop_reason"] = f"Directory does not exist: {memory_dir}"
        return result

    mdfiles = sorted(path.glob("*.md"))
    result["file_count"] = len(mdfiles)

    if len(mdfiles) > max_files:
        result["stopped"] = True
        result["stop_reason"] = (
            f"Found {len(mdfiles)} .md files (limit: {max_files}). "
            "Manual confirmation required before proceeding."
        )
        # Still include basic info about what was found
        for i, f in enumerate(mdfiles):
            entry: dict = {
                "file_code": file_code(i),
                "path_hash": path_hash(str(f)),
                "size_bytes": f.stat().st_size if f.is_file() else 0,
                "modified_at": datetime.fromtimestamp(
                    f.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
                "frontmatter_keys": [],
                "status": "unknown",
                "type": "unknown",
                "updated": None,
                "tags": [],
                "heading_count": 0,
                "headings_sample": [],
                "markdown_link_count": 0,
                "wiki_link_count": 0,
                "issue_candidates": [
                    "Exceeded max-files limit — review skipped"
                ],
            }
            if include_filenames:
                entry["filename"] = f.name
            result["files"].append(entry)
        return result

    for i, f in enumerate(mdfiles):
        entry: dict = {
            "file_code": file_code(i),
            "path_hash": path_hash(str(f)),
            "size_bytes": f.stat().st_size if f.is_file() else 0,
            "modified_at": datetime.fromtimestamp(
                f.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
            "frontmatter_keys": [],
            "status": "unknown",
            "type": "unknown",
            "updated": None,
            "tags": [],
            "heading_count": 0,
            "headings_sample": [],
            "markdown_link_count": 0,
            "wiki_link_count": 0,
            "issue_candidates": [],
        }
        if include_filenames:
            entry["filename"] = f.name

        issues: list[str] = []

        # Read file
        raw = f.read_text(encoding="utf-8")
        size = len(raw.encode("utf-8"))

        if size > LARGE_FILE_THRESHOLD:
            issues.append(
                f"File is large ({size / 1024:.0f} KB > "
                f"{LARGE_FILE_THRESHOLD / 1024:.0f} KB limit)"
            )

        # Extract frontmatter
        fm, body_start = extract_frontmatter(raw)
        entry["frontmatter_keys"] = list(fm.keys())
        if not fm:
            issues.append("Missing frontmatter")
        else:
            # Check required keys
            for key in ("name", "description", "type"):
                if key not in fm:
                    issues.append(f"Missing required frontmatter key: {key}")

            # Type validation
            valid_types = {"user", "feedback", "project", "reference"}
            fm_type = fm.get("type", "").lower()
            if fm_type:
                entry["type"] = fm_type
                if fm_type not in valid_types:
                    issues.append(
                        f"Invalid type '{fm_type}'; "
                        f"expected one of {valid_types}"
                    )
            else:
                issues.append("Missing 'type' in frontmatter")

            entry["status"] = fm.get("status", "unknown")
            entry["updated"] = fm.get("updated", None)
            entry["tags"] = [
                t.strip() for t in fm.get("tags", "").split(",") if t.strip()
            ]

            # Staleness check
            if entry.get("status") in ("active", "current") and not entry.get(
                "updated"
            ):
                issues.append(
                    "Status is 'active/current' but no 'updated' field"
                )

            # Parse tags from frontmatter (could be YAML list or comma-sep)
            tags_raw = fm.get("tags", "")
            if tags_raw.startswith("["):
                tags_raw = tags_raw.strip("[]").replace('"', "").replace(
                    "'", ""
                )
            entry["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]

        # Check for sensitive content
        sensitive_issues = check_sensitive(raw, f.name)
        issues.extend(sensitive_issues)

        # Heading analysis
        headings = extract_headings(raw, body_start)
        entry["heading_count"] = len(headings)
        entry["headings_sample"] = headings[:MAX_HEADINGS_SAMPLE]

        if not headings:
            issues.append("File has no headings")
        else:
            hierarchy_issues = check_heading_hierarchy(headings)
            issues.extend(hierarchy_issues)

        # Link analysis
        md_links, wiki_links = extract_links(raw)
        entry["markdown_link_count"] = md_links
        entry["wiki_link_count"] = wiki_links

        # Index file check: MEMORY.md should have links
        if f.name == "MEMORY.md" and md_links == 0 and wiki_links == 0:
            issues.append("Index file (MEMORY.md) has no links")

        entry["issue_candidates"] = issues
        result["files"].append(entry)

    # Global index analysis
    mem_index = None
    for f in mdfiles:
        if f.name == "MEMORY.md":
            mem_index = f
            break
    if mem_index is None:
        result["global_issues"].append("No MEMORY.md index file found")
    else:
        # Check each file has a corresponding index entry
        mem_text = mem_index.read_text(encoding="utf-8")
        for entry in result["files"]:
            if entry["file_code"] == file_code(
                next(
                    i
                    for i, f in enumerate(mdfiles)
                    if f.name == "MEMORY.md"
                )
            ):
                continue
            if include_filenames:
                filename = entry.get("filename", "")
            else:
                # Use path_hash to correlate
                filename = None
            # Simple check: filename appears in MEMORY.md
            if include_filenames and filename:
                if filename not in mem_text:
                    entry["issue_candidates"].append(
                        f"File '{filename}' not referenced in MEMORY.md index"
                    )

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit Claude memory markdown files for consistency"
    )
    parser.add_argument(
        "--memory-dir",
        default=DEFAULT_MEMORY_DIR,
        help=f"Memory directory path (default: {DEFAULT_MEMORY_DIR})",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help=f"Maximum files before stopping (default: {DEFAULT_MAX_FILES})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--include-filenames",
        action="store_true",
        help="Include real filenames in output (default: file codes only)",
    )
    args = parser.parse_args()

    report = audit_directory(
        memory_dir=args.memory_dir,
        max_files=args.max_files,
        include_filenames=args.include_filenames,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Memory Consistency Audit")
        print(f"{'='*60}")
        print(f"Scope: {report['scope']}")
        print(f"Files found: {report['file_count']}")
        if report["stopped"]:
            print(f"STOPPED: {report['stop_reason']}")
        else:
            print(f"\nFiles:")
            for entry in report["files"]:
                print(f"  {entry['file_code']}")
                print(f"    Size: {entry['size_bytes']} bytes")
                print(f"    Modified: {entry['modified_at']}")
                print(f"    Type: {entry['type']}")
                print(f"    Status: {entry['status']}")
                print(f"    Updated: {entry['updated'] or '(not set)'}")
                print(f"    Headings: {entry['heading_count']}")
                if entry["issue_candidates"]:
                    for iss in entry["issue_candidates"]:
                        print(f"    ⚠ {iss}")
            if report["global_issues"]:
                print(f"\nGlobal Issues:")
                for iss in report["global_issues"]:
                    print(f"  ⚠ {iss}")


if __name__ == "__main__":
    main()
