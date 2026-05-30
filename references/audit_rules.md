# Audit Rules Reference

Executable rules for the memory consistency auditor. Each rule includes a trigger condition, judgement criteria, and recommended action.

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
| R4.2 | Some files have `tags`, some don't | Flag as P3. Suggest consistent taxonomy. |
| R4.3 | `type` casing differs (e.g., `User` vs `user`) | Flag as P3. Normalize to lowercase. |
| R4.4 | Frontmatter key order differs significantly | Flag as P3 only if >50% of files disagree. |
| R4.5 | Body heading level skips (e.g., h1 → h3 with no h2) | Flag as P3. Suggest fixing heading hierarchy. |
| R4.6 | Filename convention differs (snake_case vs kebab-case) | Flag as P2 if inconsistent within the set. |

**Convention standard** (for this project):
- Filenames: `snake_case`
- `name` field: same as filename (without `.md`), snake_case
- `type`: lowercase — `user`, `feedback`, `project`, `reference`
- Frontmatter order: `name` → `description` → `type` (→ `originSessionId` optional)

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
| R6.1 | Any file contains `KEY=`, `SECRET=`, `TOKEN`, `password` | STOP. Show location (file code + line range) without revealing content. |
| R6.2 | File count > max-files | STOP. List file codes and ask for confirmation. |
| R6.3 | File > 50 KB | STOP. Too large for automated audit. |
| R6.4 | Proposed merge of two files | Show diff, ask for confirmation. |
| R6.5 | Proposed deletion of a file | Show summary, ask for confirmation. |

---

## 7. Auto-patchable (safe to generate diff without confirmation)

**Trigger:** Low-risk, mechanical changes.

| Rule | Condition | Can Generate Diff? |
|------|-----------|-------------------|
| R7.1 | Frontmatter `name` doesn't match filename | Yes — mechanical rename |
| R7.2 | Missing `description` in frontmatter | No — requires human judgement |
| R7.3 | Index description mismatched | Yes — align to frontmatter `description` |
| R7.4 | Inconsistent `type` casing | Yes — normalize to lowercase |
| R7.5 | Broken markdown link (internal) | No — verify target first |
| R7.6 | Typo in `type` field (e.g., `feeback` → `feedback`) | Yes — obvious fix |

---

## 8. Never Auto-modify

**Trigger:** These actions must never be taken autonomously.

| Rule | Rule |
|------|------|
| R8.1 | Never delete a memory file without explicit user confirmation |
| R8.2 | Never edit content body of a memory file without a confirmed diff |
| R8.3 | Never merge two files without the user reviewing the combined content |
| R8.4 | Never change `originSessionId` or metadata the user did not ask to change |
| R8.5 | Never expose full raw content in output, logs, or error messages |
