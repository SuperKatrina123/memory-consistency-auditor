# Audit Rules Reference

Executable rules for the memory consistency auditor. Each rule includes a trigger condition, judgement criteria, and recommended action.

---

## 0. Budget Rules

| Rule | Condition | Action |
|------|-----------|--------|
| R0.1 | Reading `memory/*.md` files | Counts as 1 read group batch, regardless of file count |
| R0.2 | Writing an audit report | Counts as 1 write group |
| R0.3 | Writing a patch file | Counts as 1 write group |
| R0.4 | Total I/O batches > 3 | Flag budget exceeded. Report and ask user for direction. |

---

## 1. Content Staleness

**Trigger:** File `updated` field exists and is >30 days old from today, OR no `updated` field with `status: active`.

| Rule | Condition | Action |
|------|-----------|--------|
| R1.1 | `updated` > 30 days ago | Flag as stale. Ask user if content should be refreshed or archived. |
| R1.2 | `status: active` but no `updated` field | Flag as missing timestamp. Suggest adding `updated` or setting `status: archived`. |
| R1.3 | File references a specific date >60 days ago | Check if the reference is still relevant. Flag if likely outdated. |
| R1.4 | Project memory references "next steps" from an old session | Flag — next steps from older sessions are likely stale or already handled. |

**Exception:** Reference-type memories (e.g., proxy config pattern) are not stale if the pattern is still valid, regardless of age.

---

## 2. Index Pointer Errors

**Trigger:** Mismatch between `MEMORY.md` index entries and actual files.

| Rule | Condition | Action |
|------|-----------|--------|
| R2.1 | Index links to `file.md` but file doesn't exist | Broken link. Flag as P1. |
| R2.2 | File exists but has no index entry | Orphan file. Flag as P1. Suggest adding to index or deleting. |
| R2.3 | Index description contradicts frontmatter `description` | Flag as P2. Suggest aligning one direction. |
| R2.4 | Index entry filename differs from actual filename (case or spelling) | Flag as P1 — links will 404 in some renderers. |

**Index link resolution:**
- The `audit_memory.py` script must attempt to resolve all links found in the index file against actual files in the target directory
- In `strict_local_audit` mode: do not output real link text or real filenames — only structured counts (resolved, missing, ambiguous, unresolved)
- If `missing_count > 0` or `ambiguous_count > 0`: flag as **medium risk**
- Never let the LLM guess which files a broken link refers to

---

## 3. Cross-file Conflicts

**Trigger:** Two or more files make contradictory claims.

| Rule | Condition | Action |
|------|-----------|--------|
| R3.1 | Same `type` + same topic, different conclusions | Flag as conflict. Ask user to disambiguate or merge. |
| R3.2 | Feedback file contradicts another feedback file | Flag as conflict. User preference may have changed — confirm which is current. |
| R3.3 | Project memory and user profile disagree on tech stack | Flag as P2. Likely one is outdated. |

---

## 4. Format Inconsistency

**Trigger:** Files in the same set use different frontmatter keys, naming conventions, or structure.

| Rule | Condition | Action |
|------|-----------|--------|
| R4.1 | `name` field uses hyphens vs underscores inconsistently | Flag as P3. Suggest aligning to project convention. |
| R4.2 | Missing `status` field in frontmatter | **Medium risk.** Flag as P2. See section 4.5. |
| R4.3 | Missing `updated` field in frontmatter | **Medium risk.** Flag as P2. See section 4.5. |
| R4.4 | Missing `type` field in frontmatter | **Medium risk.** Flag as P2. See section 4.5. |
| R4.5 | `type` casing differs (e.g., `User` vs `user`) | Flag as P3. Normalize to lowercase. |
| R4.6 | Frontmatter key order differs significantly | Flag as P3 only if >50% of files disagree. |
| R4.7 | Body heading level skips (e.g., h1 → h3 with no h2) | Flag as P3. Suggest fixing heading hierarchy. |
| R4.8 | Filename convention differs (snake_case vs kebab-case) | Flag as P2 if inconsistent within the set. |

**Convention standard** (for this project):
- Filenames: `snake_case`
- `name` field: same as filename (without `.md`), snake_case
- `type`: lowercase — `user`, `feedback`, `project`, `reference`
- Frontmatter order: `name` → `description` → `type` → `status` → `updated` → `tags` → (`originSessionId` optional)

### 4.5 Required Frontmatter Rules

All non-index memory files should contain:

```yaml
---
type: project | user | feedback | reference
status: active | archived | deprecated | needs-review
updated: YYYY-MM-DD
tags: []
---
```

| Rule | Condition | Risk | Recommendation |
|------|-----------|------|----------------|
| R4.5.1 | Missing `status` | **Medium** | Add `status: active` if current, `status: archived` if superseded |
| R4.5.2 | Missing `updated` | **Medium** | Add `updated: YYYY-MM-DD` with the last relevant date |
| R4.5.3 | Missing `type` | **Medium** | Add one of: user, feedback, project, reference |
| R4.5.4 | Missing `tags` | **Low** | Consider adding for better searchability |
| R4.5.5 | MEMORY.md or index files without frontmatter | **Allowed** | Must be identified as `index` role in the report |

---

## 5. Redundancy / Merge Candidates

**Trigger:** Overlapping content that should be consolidated.

| Rule | Condition | Action |
|------|-----------|--------|
| R5.1 | Two files about the same topic | Suggest merge. Output a combined diff. |
| R5.2 | Feedback that has been repeatedly confirmed | Can be summarized into a single consolidated feedback entry. |
| R5.3 | Project memory superseded by newer session | Flag for archival (not deletion). Move to a `status: archived` convention. |
| R5.4 | Reference that duplicates another reference | Suggest merge. Keep the more complete version. |

---

## 6. Mandatory Human Confirmation

**Trigger:** These conditions always require a human in the loop.

| Rule | Condition | Action Required |
|------|-----------|----------------|
| R6.1 | Any file contains sensitive patterns (API key, token, secret, private key, credential, `.env.local`) | **Block the file.** Do not stop audit. Show file code + fact of blocking without revealing content. Do not generate patches for blocked files. |
| R6.2 | File count > max-files | STOP. List file codes and ask for confirmation. |
| R6.3 | File > 50 KB | STOP. Too large for automated audit. |
| R6.4 | Proposed merge of two files | Show diff, ask for confirmation. |
| R6.5 | Proposed deletion of a file | Show summary, ask for confirmation. |

### 6.1 Patch Mode Entry

Patch Mode requires **all** of the following before any unified diffs can be generated:

| Condition | Check |
|-----------|-------|
| User explicitly confirms Patch Mode | Required |
| Script runs with `--include-filenames=true` | Required |
| No unresolved sensitive content | Required |
| No blocked files | Required |
| All stop conditions resolved | Required |

---

## 7. Auto-patchable (safe to generate diff without confirmation)

**Trigger:** Low-risk, mechanical changes. Applies **only in Patch Mode**.

| Rule | Condition | Can Generate Diff? |
|------|-----------|-------------------|
| R7.1 | Frontmatter `name` doesn't match filename | Yes — mechanical rename |
| R7.2 | Missing `description` in frontmatter | No — requires human judgement |
| R7.3 | Index description mismatched | Yes — align to frontmatter `description` |
| R7.4 | Inconsistent `type` casing | Yes — normalize to lowercase |
| R7.5 | Broken markdown link (internal) | No — verify target first |
| R7.6 | Typo in `type` field (e.g., `feeback` → `feedback`) | Yes — obvious fix |

---

## 8.5 Blocked File Handling

**Trigger:** A file is marked as `blocked` by the audit script.

| Rule | Condition | Action |
|------|-----------|--------|
| R8.5.1 | File marked as blocked | Block does **not** stop the full audit — continue processing other files |
| R8.5.2 | File marked as blocked | Block **does** block normal patch generation — no unified diff for this file |
| R8.5.3 | File marked as blocked | Must enter Secure Redaction Mode separately to handle |
| R8.5.4 | Blocked file has been redacted | Re-run audit to verify block is cleared before proceeding |

---

## 9. Secure Redaction Mode

**Trigger:** Entered when blocked files need sensitive content removed.

| Rule | Condition | Action |
|------|-----------|--------|
| R9.1 | Entering Secure Redaction Mode | User must explicitly confirm |
| R9.2 | Before any modification | Create backup: `.backup/<timestamp>/` |
| R9.3 | Sensitive value detected | Replace with `***` only — never output original |
| R9.4 | Entire credential block (e.g., `.env.local`) | Replace with redacted comment + `***` values |
| R9.5 | Diff containing original secret | Never generate — forbidden by R8.9 |
| R9.6 | After redaction | Re-run `audit_memory.py`, verify block cleared |
| R9.7 | Redaction confirmed successful | May delete backup or keep as rollback |

---

## 10. Post-governance Verification

**Trigger:** After any Patch Mode or Secure Redaction Mode operation completes.

| Rule | Condition | Action |
|------|-----------|--------|
| R10.1 | Governance action completed | Re-run Strict Local Audit on the full memory directory |
| R10.2 | Post-audit results ready | Compare against governance checklist (see SKILL.md §10) |
| R10.3 | All checks pass | Conclude as **Pass** |
| R10.4 | Only needs-review or low-risk issues | Conclude as **Partial pass**, list remaining items |
| R10.5 | Blocked files / high risk / index failure | Conclude as **Fail**, return to appropriate Step |

---

## 11. Never Auto-modify

**Trigger:** These actions must never be taken autonomously.

| Rule | Rule |
|------|------|
| R11.1 | Never delete a memory file without explicit user confirmation |
| R11.2 | Never edit content body of a memory file without a confirmed diff |
| R11.3 | Never merge two files without the user reviewing the combined content |
| R11.4 | Never change `originSessionId` or metadata the user did not ask to change |
| R11.5 | Never expose full raw content in output, logs, or error messages |
| R11.6 | Never generate unified diffs outside of Patch Mode |
| R11.7 | Never generate patches for blocked files |
| R11.8 | Never output original secret/credential values in any mode |
| R11.9 | Never generate diffs containing original secret values — use Secure Redaction Mode instead |
| R11.10 | Never delete backup before user confirms redaction is successful |
