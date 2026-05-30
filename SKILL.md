---
name: memory-consistency-auditor
description: Audit local Claude memory markdown files for consistency, staleness, index pointer accuracy, formatting drift, duplicate content, and governance risks. Use when the user mentions memory audit, 记忆文件审查, memory consistency, memory/*.md, Personal Cognitive OS, long-term memory cleanup, or index pointer validation.
---

# memory-consistency-auditor

## 1. Purpose

Review a set of Claude memory `.md` files (by default in `~/.claude/projects/-Users-sakura/memory/`) for structural and semantic consistency. The auditor does **not** summarize or rewrite memory content — it checks:

- Whether index pointers resolve correctly
- Whether files are stale, conflicting, or redundant
- Whether frontmatter and formatting follow conventions
- Whether the set exceeds size limits or contains sensitive data

## 2. Default Scope

| Field | Value |
|-------|-------|
| Target directory | `~/.claude/projects/-Users-sakura/memory/` |
| File pattern | `*.md` only |
| Expected file count | 6 |
| Allowed external dependencies | Python 3 stdlib only |

## 3. Privacy Boundary

1. Only access `~/.claude/projects/-Users-sakura/memory/*.md`
2. Do not read files outside the target directory
3. Do not write outside the target directory
4. Do not call network, browser, external API, or MCP tools
5. Do not output raw memory content — use placeholder references
6. Do not output real filenames by default — use `File A / File B / File C` codes
7. Do not modify memory files unless the user explicitly confirms
8. If modifications are needed, output only unified diff patches
9. If more than `max-files` are found, stop and ask for confirmation
10. If suspected sensitive content is detected, stop and ask for confirmation

## 4. Budget Limits

| Resource | Limit |
|----------|-------|
| LLM inference calls | ≤ 1 |
| File read/write operations | ≤ 3 (metadata-only reads by script) |
| Output length | ≤ 300 lines |
| Strategy | Prefer local script for structured scan, then feed metadata to LLM |

Priority: local script > structured metadata > LLM judgement. Minimise what the LLM sees.

## 5. Execution Modes

### 5.1 Strict Local Audit (preferred)

1. Run `python scripts/audit_memory.py --json` to produce a structured metadata-only JSON report
2. Hand the JSON to the LLM for analysis
3. LLM produces the audit report from metadata alone, never reading raw files

```
flow: audit_memory.py (raw access) → JSON metadata → LLM analysis → audit report
```

### 5.2 Practical Claude Code Audit (fallback)

When the Python script cannot be executed (no Python, permission denied, etc.):

1. Use Glob tool to list `*.md` files in the target directory
2. If count > max-files, STOP
3. Use Read tool only to read frontmatter (first ~10 lines) of each file
4. Use Read tool only to check heading structure (grep for `^#`)
5. Do not read full file bodies
6. Follow the same output format and privacy rules

## 6. Audit Checklist

For each file, check:

- [ ] Frontmatter exists with valid YAML
- [ ] Required keys present: `name`, `description`, `type`
- [ ] `type` is one of: `user`, `feedback`, `project`, `reference`
- [ ] `description` is non-empty and accurate for the content
- [ ] Index entry in `MEMORY.md` matches filename
- [ ] Index description matches frontmatter `description`
- [ ] Cross-references between files resolve to existing files
- [ ] No duplicate or overlapping content across files
- [ ] Content not obviously stale (project status, outdated references)
- [ ] No sensitive data (API keys, tokens, passwords, full email addresses)
- [ ] No wiki-links `[[]]` pointing to non-existent files
- [ ] No broken markdown links
- [ ] No inconsistent naming conventions (`name` field vs filename)
- [ ] No conflicting statements between files

For the file set as a whole, check:

- [ ] File count does not exceed limit
- [ ] No files are oversized (>50 KB)
- [ ] MEMORY.md index is complete and accurate
- [ ] No redundant files that should be merged
- [ ] No files that should be archived (superseded / resolved)

## 7. Required Output Format

Use the template in `templates/audit_report.md`. Must include:

```
## 操作记录
## 审查结果总览
## 一致性问题
## 建议 Patch
## 需要人工确认的点
## 复盘
```

## 8. Patch Rule

- All proposed modifications must be in unified diff format
- Every diff must be accompanied by a rationale
- No diffs are applied automatically — user must confirm each one
- Each diff must be scoped to a single change (one concern per diff)

## 9. Stop Conditions

Execution **must stop immediately** and ask for user confirmation when:

| Condition | Check |
|-----------|-------|
| File count > max-files | Script reports `stopped: true` |
| Any file looks sensitive (API keys, secrets, PII) | Manual review required |
| A file is too large (>50 KB) | Manual review required |
| MEMORY.md index is not found | Cannot proceed without index |
| Target directory does not exist | Cannot proceed |
