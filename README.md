# memory-consistency-auditor

审查本地 Claude 记忆 Markdown 文件的一致性、时效性、索引准确性、格式漂移和治理风险的可复用 Skill。

## 结构

```
memory-consistency-auditor/
├── SKILL.md                    # Skill 主规约
├── scripts/
│   └── audit_memory.py         # 本地结构化扫描脚本（Python3，仅 stdlib）
├── references/
│   └── audit_rules.md          # 8 大类可执行审计规则
└── templates/
    └── audit_report.md         # 固定报告模板
```

## 快速开始

```bash
# 直接运行本地扫描
python3 scripts/audit_memory.py --json

# 指定目录
python3 scripts/audit_memory.py --memory-dir /path/to/memory --json

# 查看所有参数
python3 scripts/audit_memory.py --help
```

## 作为 Claude Skill 使用

将此目录复制到 `~/.claude/skills/`：

```bash
cp -r memory-consistency-auditor ~/.claude/skills/memory-consistency-auditor
```

然后在新会话中触发：

```
/memory-consistency-auditor
```

## 治理边界

- 只访问目标目录下的 `*.md` 文件
- 默认不输出真实文件名（使用 File A / File B 代号）
- 不输出原始内容
- 超过 6 个文件自动停止
- 发现疑似敏感内容自动停止
- 建议修改只以 unified diff 格式输出

## 预算限制

- LLM 调用 ≤ 1 次
- 文件读写 ≤ 3 次
- 输出 ≤ 300 行
- 优先本地脚本做结构化扫描
