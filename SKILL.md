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
10. If suspected sensitive content is detected, **block the file** and continue audit — do not stop the entire audit
11. Blocked files: do not output matched content, do not output surrounding context, do not generate patches for blocked files

## 4. Budget Limits

| Resource | Limit |
|----------|-------|
| LLM inference calls | ≤ 1 |
| File I/O batches | ≤ 3 |
| Output length | ≤ 300 lines |
| Strategy | Prefer local script for structured scan, then feed metadata to LLM |

**File I/O batch definition:**
- Batch reading `memory/*.md` counts as **1 read group** (reading 6 files in one batch is not 6 separate violations)
- Optionally writing one audit report file counts as **1 write group**
- Optionally writing one patch file counts as **1 write group**
- Total I/O batches = read groups + write groups

Priority: local script > structured metadata > LLM judgement. Minimise what the LLM sees.

## 5. Execution Modes

### 5.1 Strict Local Audit (preferred)

1. Run `python scripts/audit_memory.py --json` to produce a structured metadata-only JSON report
2. Hand the JSON to the LLM for analysis
3. LLM produces the audit report from metadata alone, never reading raw files

```
flow: audit_memory.py (raw access) → JSON metadata → LLM analysis → audit report
```

**Strict Local Audit boundaries:**
- Do not output real filenames
- Do not output real file paths
- Do not output original text content
- Do not output long summaries
- Do not generate real unified diffs
- Only output **patch intentions** (what needs to change and why, without real paths/content)
- If real file paths are needed for modification, require the user to explicitly enter Patch Mode

### 5.2 Practical Claude Code Audit (fallback)

When the Python script cannot be executed (no Python, permission denied, etc.):

1. Use Glob tool to list `*.md` files in the target directory
2. If count > max-files, STOP
3. Use Read tool only to read frontmatter (first ~10 lines) of each file
4. Use Read tool only to check heading structure (grep for `^#`)
5. Do not read full file bodies
6. Follow the same output format and privacy rules

### 5.3 Patch Mode

Patch Mode is a higher-privilege mode for generating actionable file modifications.

**Entry conditions (ALL must be satisfied):**
- User explicitly confirms entering Patch Mode
- Script runs with `--include-filenames=true`
- No unresolved sensitive content in any file
- No blocked files remaining
- All stop conditions resolved

**Patch Mode rules:**
- Only generate diffs within user-confirmed scope
- All proposed modifications must be in unified diff format
- Every diff must be accompanied by a rationale
- No diffs are applied automatically — user must explicitly confirm each one
- Each diff must be scoped to a single change (one concern per diff)

### 5.4 Secure Redaction Mode

Secure Redaction Mode is a restricted mode for handling blocked files that contain sensitive content (API keys, tokens, secrets, credentials).

**Entry conditions (ALL must be satisfied):**
- User explicitly confirms entering Secure Redaction Mode
- Blocked files have been identified and confirmed by the user
- Backup of blocked files has been created (`.backup/<timestamp>/`)

**Secure Redaction Mode rules:**
- Do NOT output original secret/credential values
- Do NOT generate unified diffs that contain original secret values
- Only replace matched sensitive values with `***`
- For entire `.env.local` / credential code blocks, replace with redacted placeholder and note
- Must create backup or ensure rollback capability before any modification
- After redaction, re-run `audit_memory.py` to verify block is cleared
- Never output matched content, surrounding context, or original values to terminal

## 6. Audit Checklist

For each file, check:

- [ ] Frontmatter exists with valid YAML
- [ ] Required keys present: `type`, `status`, `updated`
- [ ] `type` is one of: `user`, `feedback`, `project`, `reference`
- [ ] `status` is one of: `active`, `archived`, `deprecated`, `needs-review`
- [ ] `updated` field is present if `status` is `active` or `current`
- [ ] `description` is non-empty and accurate for the content
- [ ] `tags` present (low risk if missing)
- [ ] Each non-index file has at least one h2 heading
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

**Required frontmatter format for all non-index files:**

```yaml
---
type: project | user | feedback | reference
status: active | archived | deprecated | needs-review
updated: YYYY-MM-DD
tags:
  - tag1
  - tag2
---
```

**Risk levels:**
- Missing `status`: **medium risk**
- Missing `updated`: **medium risk**
- Missing `type`: **medium risk**
- Missing `tags`: **low risk**
- Missing h2 heading: **medium risk**
- MEMORY.md / index files may lack frontmatter but must pass index_validation

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
## 模式与边界
## 审查结果总览
## Blocked Files (if any)
## 一致性问题
## Patch Intentions (Strict Local Audit) or Patch (Patch Mode)
## 需要人工确认的点
## 复盘
```

## 8. Patch Rule

- In **Strict Local Audit** mode: only output **patch intentions** — describe what to change and why, without real paths or content
- In **Patch Mode**: output unified diffs with real filenames, only within user-confirmed scope
- In **Secure Redaction Mode**: do not output diffs that contain original secret values
- Every diff must be accompanied by a rationale
- No diffs are applied automatically — user must confirm each one
- Each diff must be scoped to a single change (one concern per diff)

## 9. Stop Conditions

Execution **must stop immediately** and ask for user confirmation when:

| Condition | Check |
|-----------|-------|
| File count > max-files | Script reports `stopped: true` |
| A file is too large (>50 KB) | Manual review required |
| MEMORY.md index is not found | Cannot proceed without index |
| Target directory does not exist | Cannot proceed |

Sensitive content does **not** stop the audit — it blocks the affected file and continues.

## 10. Post-governance Verification

After any governance action (Patch Mode or Secure Redaction Mode), the audit must be re-run in Strict Local Audit mode as final verification.

**Verification checklist:**
- [ ] Re-run `python scripts/audit_memory.py --json`
- [ ] All non-index files have `status`
- [ ] All non-index files have `updated`
- [ ] All non-index files have `tags`
- [ ] All non-index files have at least one heading
- [ ] index_validation: all resolved
- [ ] No blocked files remaining
- [ ] No high risk issues
- [ ] No new issues introduced

**Final verdict:**
- **Pass**: No blocked files, no high risk, index fully resolved, all fields complete, no new issues
- **Partial pass**: Only needs-review files remaining, or low-risk format issues only
- **Fail**: Blocked files remain, high risk issues exist, index validation fails, or new sensitive risks appear
