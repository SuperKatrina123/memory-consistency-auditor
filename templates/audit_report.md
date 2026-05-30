# Memory Consistency Audit Report

**Audit Date:** {{date}}
**Mode:** {{mode | strict_local_audit | practical_claude_code_audit}}
**Scope:** {{memory_directory}}

---

## 操作记录

| 步骤 | 操作 | 结果 |
|------|------|------|
| 1 | 扫描目标目录 | {{file_count}} 个 .md 文件 |
| 2 | 提取 frontmatter 元数据 | {{files_with_frontmatter}}/{{file_count}} 通过 |
| 3 | 校验索引指针 | {{index_issues}} 个问题 |
| 4 | 交叉比对文件间一致性 | {{conflict_count}} 个冲突 |
| 5 | 检查格式统一性 | {{format_issues}} 个问题 |

---

## 模式与边界

| 字段 | 值 |
|------|-----|
| 执行模式 | {{strict_local_audit / practical / patch_mode}} |
| 真实文件名输出 | {{yes / no}} |
| 原文输出 | {{yes / no}} |
| Blocked Files | {{count}} |
| Patch 状态 | {{intention_only / unified_diff_generated}} |

---

## 审查结果总览

| 文件代号 | 文件角色 | 状态 | 问题 | 风险 | 建议 | Blocked |
|----------|----------|------|------|------|------|---------|
| File A | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} | {{yes/no}} |
| File B | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} | {{yes/no}} |
| File C | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} | {{yes/no}} |
| File D | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} | {{yes/no}} |
| File E | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} | {{yes/no}} |
| File F | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} | {{yes/no}} |

---

## Blocked Files

| 文件代号 | 原因 | 处理方式 |
|----------|------|----------|
| {{file_code}} | Sensitive pattern detected (API key / token / credential) | 不输出匹配内容，不输出上下文原文，不为该文件生成 patch。需人工确认后解除 block。 |

---

## 一致性问题

### 1. 内容过时

| 文件代号 | 问题描述 | 严重程度 |
|----------|----------|----------|
| {{file_code}} | {{description}} | {{P0/P1/P2/P3}} |

### 2. 索引指针错误

| 文件代号 | 索引声明 | 实际状态 | 差异 |
|----------|----------|----------|------|
| {{file_code}} | {{index_says}} | {{actual}} | {{gap}} |

**Index Validation (local resolve):**
| 指标 | 数值 |
|------|------|
| 索引文件 | {{File A / other}} |
| 链接数 | {{count}} |
| 可解析 | {{count}} |
| 缺失 | {{count}} |
| 歧义 | {{count}} |
| 无法解析 | {{count}} |
| 风险等级 | {{low / medium / high}} |

### 3. 文件间冲突

| 涉及文件 | 冲突描述 | 建议 |
|----------|----------|------|
| {{files}} | {{conflict_description}} | {{resolution}} |

### 4. 格式不统一

| 文件代号 | 字段 | 当前值 | 风险 | 建议值 |
|----------|------|--------|------|--------|
| {{file_code}} | {{field_name}} | {{current}} | {{low/medium/high}} | {{suggested}} |

### 5. 冗余或可合并内容

| 涉及文件 | 重叠内容 | 建议操作 |
|----------|----------|----------|
| {{files}} | {{overlap_description}} | merge / archive / delete |

---

## Patch Intentions

（Strict Local Audit 模式下仅输出修改意图，不输出真实文件路径和原文。）

### Patch Intention 1: {{description}}

- **目标文件:** {{file_code}}
- **修改类型:** field update / rename / restructure
- **原因:** {{rationale}}
- **具体操作:** {{what_to_change_without_exposing_content}}

---

### Patch Intention 2: {{description}}

- **目标文件:** {{file_code}}
- **修改类型:** field update / rename / restructure
- **原因:** {{rationale}}
- **具体操作:** {{what_to_change_without_exposing_content}}

---

## Patch

（仅 Patch Mode 输出。Strict Local Audit 模式下此项不启用。）

### Patch 1: {{description}}

```diff
--- a/{{filename}}
+++ b/{{filename}}
@@ -{{start}},{{count}} +{{start}},{{count}} @@
-{{old_line}}
+{{new_line}}
```

**理由:** {{rationale}}

---

### Patch 2: {{description}}

```diff
--- a/{{filename}}
+++ b/{{filename}}
@@ -{{start}},{{count}} +{{start}},{{count}} @@
-{{old_line}}
+{{new_line}}
```

**理由:** {{rationale}}

---

## Secure Redaction Mode Note

（如果本次审计涉及 blocked 文件处理，在此注明。）

| 文件代号 | 处理方式 | 验证结果 |
|----------|----------|----------|
| {{file_code}} | redact / remove-block / manual | block cleared / pending |

注意：不输出原始敏感内容、不输出匹配行、不输出上下文。

---

## 需要人工确认的点

1. {{confirmation_point_1}}
2. {{confirmation_point_2}}
3. {{confirmation_point_3}}

---

## 治理验收

| 检查项 | 结果 |
|---|---|
| 所有非索引文件有 status | {{yes/no}} |
| 所有非索引文件有 updated | {{yes/no}} |
| 所有非索引文件有 tags | {{yes/no}} |
| 所有非索引文件有 h2 标题 | {{yes/no}} |
| index_validation 全部 resolved | {{yes/no}} |
| 无 blocked 文件 | {{yes/no}} |
| 无 high risk 问题 | {{yes/no}} |
| 无新增问题 | {{yes/no}} |

**验收结论:** {{pass / partial pass / fail}}

---

## 复盘

| 护栏 | 效果 | 说明 |
|------|------|------|
| G1 成本上限 | ✅ / ⚠️ / ❌ | {{note}} |
| G2 敏感信息处理 | ✅ / ⚠️ / ❌ | {{note}} |
| G3 输出可审查 | ✅ / ⚠️ / ❌ | {{note}} |

**本次审计暴露的规则缺口:** {{gap_description}}
