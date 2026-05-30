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
    r"(?i)\.env\.local",
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


def extract_links(text: str) -> list[tuple[str, str]]:
    """Extract markdown links and wiki links.
    Returns list of (link_text, link_target) tuples.
    For wiki links [[target]], link_text is empty.
    """
    links: list[tuple[str, str]] = []
    # Markdown links: [text](target)
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        links.append((m.group(1), m.group(2)))
    # Wiki links: [[target]]
    for m in re.finditer(r"\[\[([^\]]+)\]\]", text):
        links.append(("", m.group(1)))
    return links


def check_sensitive(text: str) -> list[str]:
    """Check for sensitive content patterns.
    Returns list of issue descriptions (without revealing the match).
    Returns empty list if no sensitive patterns found.
    """
    issues = []
    for pattern in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            lines_matched = set()
            for m in re.finditer(pattern, text):
                line_num = text[: m.start()].count("\n") + 1
                lines_matched.add(line_num)
            issues.append(
                f"Sensitive pattern detected: matched "
                f"on {len(lines_matched)} line(s)"
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


def resolve_index_links(
    index_text: str, mdfiles: list[Path], include_filenames: bool
) -> dict:
    """Resolve links from the index file against actual files.
    Returns structured result without exposing real names in strict mode.
    """
    links = extract_links(index_text)
    md_link_targets = [target for _, target in links if target.endswith(".md")]
    existing_filenames = {f.name for f in mdfiles}

    resolved = 0
    missing = 0
    ambiguous = 0
    unresolved = 0
    unresolved_targets: list[str] = []

    for target in md_link_targets:
        target_clean = target.split("#")[0].split("?")[0]  # strip anchor/query
        if not target_clean:
            continue
        if target_clean in existing_filenames:
            resolved += 1
        else:
            # Try matching without extension or with partial name
            candidates = [f for f in existing_filenames if target_clean in f]
            if len(candidates) == 0:
                missing += 1
                unresolved_targets.append(target_clean)
            elif len(candidates) == 1:
                resolved += 1
            else:
                ambiguous += 1
                unresolved_targets.append(target_clean)

    result: dict = {
        "link_count": len(md_link_targets),
        "resolved_count": resolved,
        "missing_count": missing,
        "ambiguous_count": ambiguous,
        "unresolved_count": missing + ambiguous,
    }

    if not include_filenames:
        # Do not expose real link targets
        pass

    return result


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
        "blocked_files": [],
        "index_validation": None,
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
                "blocked": False,
                "issue_candidates": [
                    "Exceeded max-files limit — review skipped"
                ],
            }
            if include_filenames:
                entry["filename"] = f.name
            result["files"].append(entry)
        return result

    # --- Identify index file ---
    index_file: Path | None = None
    for f in mdfiles:
        if f.name == "MEMORY.md":
            index_file = f
            break
    if index_file is None:
        for f in mdfiles:
            raw_preview = f.read_text(encoding="utf-8")
            fm, _ = extract_frontmatter(raw_preview)
            if fm.get("type", "").lower() == "index":
                index_file = f
                break

    index_file_code: str | None = None
    for i, f in enumerate(mdfiles):
        if f == index_file:
            index_file_code = file_code(i)
            break

    # --- Scan each file ---
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
            "blocked": False,
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

        # --- Sensitive content check (before any content processing) ---
        sensitive_issues = check_sensitive(raw)
        is_sensitive = len(sensitive_issues) > 0

        if is_sensitive:
            entry["blocked"] = True
            # Add blocking issue without revealing matched content
            issues.append(
                "BLOCKED: Sensitive pattern detected (API key / token / secret / credential). "
                "No patch will be generated for this file."
            )
            result["blocked_files"].append(
                {
                    "file_code": file_code(i),
                    "reason": "Sensitive pattern detected",
                }
            )

        # --- Frontmatter extraction ---
        fm, body_start = extract_frontmatter(raw)

        # Identify role: MEMORY.md or type=index → index role
        is_index_role = (
            f.name == "MEMORY.md"
            or fm.get("type", "").lower() == "index"
        )
        if is_index_role:
            entry["type"] = "index"

        entry["frontmatter_keys"] = list(fm.keys())

        if not fm and not is_index_role:
            issues.append("Missing frontmatter")
        elif fm:
            # Required key checks (only for non-index files)
            if not is_index_role:
                for key in ("type", "status", "updated"):
                    if key not in fm:
                        risk = "low" if key == "tags" else "medium"
                        issues.append(
                            f"Missing required frontmatter key: '{key}'"
                        )

            # Type validation
            valid_types = {"user", "feedback", "project", "reference", "index"}
            fm_type = fm.get("type", "").lower()
            if fm_type:
                entry["type"] = fm_type
                if fm_type not in valid_types:
                    issues.append(
                        f"Invalid type '{fm_type}'; "
                        f"expected one of {valid_types}"
                    )
            elif not is_index_role:
                issues.append("Missing 'type' in frontmatter")

            entry["status"] = fm.get("status", "unknown")
            entry["updated"] = fm.get("updated", None)

            # Tags check
            tags_raw = fm.get("tags", "")
            if tags_raw.startswith("["):
                tags_raw = tags_raw.strip("[]").replace('"', "").replace("'", "")
            entry["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]

            # Staleness check
            if entry.get("status") in ("active", "current") and not entry.get("updated"):
                issues.append(
                    "Status is 'active/current' but no 'updated' field"
                )

        # --- Heading analysis (skip if blocked) ---
        if not is_sensitive:
            headings = extract_headings(raw, body_start)
            entry["heading_count"] = len(headings)
            entry["headings_sample"] = headings[:MAX_HEADINGS_SAMPLE]

            if not headings and not is_index_role:
                issues.append("File has no headings")
            else:
                hierarchy_issues = check_heading_hierarchy(headings)
                issues.extend(hierarchy_issues)

        # --- Link analysis ---
        links = extract_links(raw)
        if not is_sensitive:
            entry["markdown_link_count"] = sum(
                1 for _, target in links if not target.startswith("[[")
            )
            entry["wiki_link_count"] = sum(
                1 for _, target in links if target.startswith("[[")
            )

        # Index file check: should have links
        if is_index_role and not links:
            issues.append("Index file has no links")

        entry["issue_candidates"] = issues
        result["files"].append(entry)

    # --- Index validation ---
    if index_file is not None:
        index_text = index_file.read_text(encoding="utf-8")
        index_validation = resolve_index_links(index_text, mdfiles, include_filenames)
        index_validation["index_file"] = index_file_code or "unknown"
        result["index_validation"] = index_validation

        if index_validation["missing_count"] > 0 or index_validation["ambiguous_count"] > 0:
            result["global_issues"].append(
                f"Index link resolution: {index_validation['missing_count']} missing, "
                f"{index_validation['ambiguous_count']} ambiguous — medium risk"
            )
    else:
        result["global_issues"].append("No index file (MEMORY.md or type=index) found")

    # --- Global orphan check ---
    if include_filenames and index_file is not None:
        index_text = index_file.read_text(encoding="utf-8")
        for entry in result["files"]:
            if entry["file_code"] == index_file_code:
                continue
            filename = entry.get("filename", "")
            if filename and filename not in index_text:
                entry["issue_candidates"].append(
                    f"File '{filename}' not referenced in index"
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
            if report["index_validation"]:
                iv = report["index_validation"]
                print(f"\nIndex Validation:")
                print(f"  Index file: {iv['index_file']}")
                print(f"  Links: {iv['link_count']}")
                print(f"  Resolved: {iv['resolved_count']}")
                print(f"  Missing: {iv['missing_count']}")
                print(f"  Ambiguous: {iv['ambiguous_count']}")
            if report["blocked_files"]:
                print(f"\nBlocked Files:")
                for bf in report["blocked_files"]:
                    print(f"  ⛔ {bf['file_code']}: {bf['reason']}")
            print(f"\nFiles:")
            for entry in report["files"]:
                print(f"  {entry['file_code']}")
                if entry["blocked"]:
                    print(f"    ⛔ BLOCKED")
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
