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

## 审查结果总览

| 文件代号 | 文件角色 | 状态 | 问题 | 风险 | 建议 |
|----------|----------|------|------|------|------|
| File A | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} |
| File B | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} |
| File C | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} |
| File D | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} |
| File E | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} |
| File F | {{role}} | {{status}} | {{issues_summary}} | {{risk_level}} | {{suggestion}} |

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

### 3. 文件间冲突

| 涉及文件 | 冲突描述 | 建议 |
|----------|----------|------|
| {{files}} | {{conflict_description}} | {{resolution}} |

### 4. 格式不统一

| 文件代号 | 字段 | 当前值 | 建议值 |
|----------|------|--------|--------|
| {{file_code}} | {{field_name}} | {{current}} | {{suggested}} |

### 5. 冗余或可合并内容

| 涉及文件 | 重叠内容 | 建议操作 |
|----------|----------|----------|
| {{files}} | {{overlap_description}} | merge / archive / delete |

---

## 建议 Patch

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

## 需要人工确认的点

1. {{confirmation_point_1}}
2. {{confirmation_point_2}}
3. {{confirmation_point_3}}

---

## 复盘

| 护栏 | 效果 | 说明 |
|------|------|------|
| G1 成本上限 | ✅ / ⚠️ / ❌ | {{note}} |
| G2 敏感信息处理 | ✅ / ⚠️ / ❌ | {{note}} |
| G3 输出可审查 | ✅ / ⚠️ / ❌ | {{note}} |

**本次审计暴露的规则缺口:** {{gap_description}}
