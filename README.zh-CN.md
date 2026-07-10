# lore

> 框架无关的 AI 编程智能体项目记忆。

一个由 AI 智能体维护的软件项目长期知识库。它捕获那些通常只存在于原始开发者脑中的上下文——架构、决策、约定——并以纯 Markdown 文件形式持久化，任何智能体都能消费。

## 解决什么问题

当你在多个 AI 工具（Claude Code、Cursor、Cline、GitHub Copilot、Aider、LangGraph agent、DeepAgents）和多个会话之间切换工作时，上下文会丢失：

- **每个新会话都要重新解释项目。** "我们用 Next.js App Router，不是 Pages。用 Zustand，不是 Redux。不要提交密钥。"
- **决策被遗忘。** "为什么选 X 不选 Y？" → "我不记得了，问问团队吧。"
- **智能体之间互相矛盾。** Cursor 读 `.cursorrules`，Claude Code 读 `CLAUDE.md`，两个文件逐渐漂移。
- **新成员上手需要数周。** 新成员 / 新 agent 都得从零学项目约定。

lore 维护一个单一事实源（`.lore/`），并把它投影到你的 agent 已经读取的配置文件里。它追踪**为什么**做某个决策，而不只是代码**做了什么**，并把这个历史跨 session、跨工具保留下来。

## 快速上手

```bash
# 1. 初始化（每个项目运行一次）
lore init
# 扫描项目，生成 entry 草案，请用户确认，创建 .lore/

# 2. 完成一个非平凡的改动后
lore sync
# 检测代码 diff，提议 [NEW]/[STALE]/[REFINED] entry，等用户裁决

# 3. 大量改动后，刷新 agent 可见的摘要
lore compress
# 重新生成 SUMMARY.md，更新 CLAUDE.md / .cursorrules 等

# 4. 强制刷新 mirror（比如手动编辑了 .lore/ 之后）
lore mirror
# 用当前状态重写 CLAUDE.md 等平台文件
```

另外三个只读命令：

```bash
lore query                          # 从记忆库回答问题，引用 entry ID
lore audit                          # 检查记忆与现实的偏差，报告写入 .lore/audit/
lore history DEC-2026-02-03-7c19    # 展示某 entry 相关代码的 git commits
lore history frontend/src/store.ts  # ...或某个文件
lore history --scope=frontend       # ...或某个 scope 下的所有 lore 文件
lore history --json                 # 机器可读
```

## `.lore/` 目录结构

```
.lore/
├── SUMMARY.md                    # 顶层摘要；新 agent 先读这个
├── _global/                      # 跨 scope 的事实
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   └── CONVENTIONS.md
├── scopes/                       # 各 scope 自己的事实（frontend / backend / shared）
│   └── <scope>/
│       ├── ARCHITECTURE.md
│       ├── DECISIONS.md
│       └── CONVENTIONS.md
├── draft/                        # init 阶段用，存待确认的草案
├── audit/                        # audit 阶段用，存报告
└── archive/                      # 旧/过期的 entry
```

每条 entry 是一个 Markdown bullet（≤ 2 行），带确定性 ID 和内联状态 tag：

```markdown
- [ARCH-2026-07-09-a3f2] Use Next.js App Router; reason: streaming + RSC. #added:2026-07-09
- [DEC-2026-02-03-7c19] Chose Zustand over Redux; reason: 60% less boilerplate. #added:2026-02-03 #verified:2026-06-15
- [CONV-2026-01-20-b1e8] Never commit secrets; use `dotenv` + `.env.local`. #added:2026-01-20
```

## 七个工作流

| 命令 | 作用 | 写什么 |
|---|---|---|
| `init` | 首次扫描项目；生成 entry 草案；用户确认 | `.lore/*` + 平台 mirror |
| `sync` | 检测代码变更；提议更新；用户裁决 | 只写 `.lore/*`（不写 mirror）|
| `query` | 只读；从记忆回答问题并引用 entry ID | 不写任何东西 |
| `audit` | 只读；检查记忆与现实；写报告 | 只写 `.lore/audit/*` |
| `compress` | 从当前 entry 生成 `SUMMARY.md` | `SUMMARY.md` + 平台 mirror |
| `mirror` | 强制重新生成平台 mirror（带内容去重）| `CLAUDE.md`、`.cursorrules` 等 |
| `history` | 只读；列出某条目/文件/scope 相关的 git commits | 无 |

`sync` **不会**更新平台 mirror。这是刻意的：mirror 文件是 agent 入口，不是变更日志。每次 sync 都重写会让 `git log` 变得很乱，稀释"人工合并"这个 mirror 应该提供的信号。当你需要 agent 视图跟上时，跑 `lore mirror`（或 `compress`）。

要恢复老行为（每次 sync 都更新 mirror），在 `.lore/.config.json` 里设 `"sync_updates_mirror": true`。

## Sync 信任级别

`sync` 根据变更类型和配置的信任级别，决定自动应用还是要求确认：

| 变更类型 | `high` | `medium`（默认）| `low` |
|---|---|---|---|
| 去重命中 | 自动 | 自动 | 确认 |
| 等价 REFINED | 自动 | 自动 | 确认 |
| `NEW` entry | 自动 | 确认 | 确认 |
| `STALE` 标记 | 自动 | 确认 | 确认 |
| `ALERT` | 确认 | 确认 | 确认 |

默认 `medium` 是平衡选择：低风险变更静默应用，真正的添加或冲突仍要你点头。完全信任 agent 切 `high`；想 review 每次变更切 `low`。

## 平台 Mirror

lore 的事实源是 `.lore/*`，但它会投影到 agent 已经读取的配置文件。targets 通过扫描 repo 根目录的现有平台文件自动检测（auto-detect）；都没找到时 `lore init` 用 multi-select 问用户想给哪些 agent 写。在 `.lore/.config.json` 显式写 `mirror_targets` 会覆盖这个行为（Replace 语义）。

| 平台 | 文件 | 自动检测？ |
|---|---|---|
| Claude Code | `CLAUDE.md` | ✅ |
| Cursor | `.cursorrules` (或 `.cursor/rules/*.mdc`) | ✅ |
| Cline | `.clinerules` | ✅ |
| Aider / Codex / OpenCode | `AGENTS.md` (或 `CONVENTIONS.md`) | ✅ |
| Windsurf | `.windsurfrules` | ✅ |
| GitHub Copilot | `.github/copilot-instructions.md` | ✅ |
| Continue.dev | `.continue/rules/lore.md` | ✅ |
| LangGraph / DeepAgents |（无文件 — 直接读 `.lore/*.md`）| n/a |

每个 mirror 文件用 `---` 分隔符切成两段：

```markdown
## Lore (auto-managed)
... Skill 从 .lore/ 写入的内容 ...

---

## My notes (free edit)
... 你手写的笔记，sync 时原样保留 ...
```

Skill 只写 `## Lore` 段。`## My notes` 段以下都是你自由编辑的区域，Skill 在每次 sync 和 compress 时原样保留。

## 脚本

`scripts/` 里的辅助脚本减少重复的机械工作：

```bash
python scripts/id_hash.py "Use Next.js App Router"        # → a3f2（4 字符 ID hash）
python scripts/list_entries.py                            # 列出所有 entry（文本）
python scripts/list_entries.py --scope=frontend --json    # 过滤的 JSON
python scripts/find_duplicates.py                          # 找可能的重复
python scripts/find_stale.py --days=90                    # 找过期的 entry
python scripts/history.py DEC-2026-02-03-7c19             # 展示某 entry 的 git 历史
```

所有脚本都是跨平台 Python 3.6+，无第三方依赖。详见 `scripts/README.md`（英文）或 `scripts/README.zh-CN.md`（中文）。

## 配置

`.lore/.config.json` 是可选的。默认值适合大多数项目。

```json
{
  "auto_mirror": false,
  "sync_updates_mirror": false,
  "sync_trust": "medium",
  "mirror_targets": ["CLAUDE.md"], // optional — auto-detected if absent
  "mirror_mode": "summary",
  "compress_thresholds": { "max_entries": 500, "max_days_since_compress": 30 },
  "sync_thresholds": { "min_lines_changed": 50, "min_directories_changed": 2 }
}
```

字段含义：见 `references/config.md`。

## 不适用场景

lore 为长期项目设计。下列场景过度：

- **短命脚本 / 一次性 demo。** 维护成本大于价值。
- **快速原型**，决策每周都变。决策追踪机制反而碍事。
- **微型单文件项目。** 用 `README.md` 就够了。
- **不希望 AI 做决策的项目。** 如果你想要纯只读 agent，lore 没有价值。
- **超大型 monorepo（50+ packages）**。Scope 树会变得难用，考虑按 package 拆分或每个 cluster 一个 sub-skill。

## FAQ

**Q: 不在 git 仓库里能用 lore 吗？**
A: 部分能。`sync` 用 `git diff` 检测变化。没有 git 仍能用 `init` / `query` / `audit` / `compress` / `mirror`，但 `sync` 需要你告诉它改了什么。

**Q: 我能直接手动编辑 `.lore/*.md` 吗？**
A: 可以。文件就是纯 Markdown。加新 entry 时用 `id_hash.py` 算 ID（保持确定性）。手动编辑后跑 `lore mirror` 同步 agent 端。

**Q: 如果我完全不想要 mirror 文件（只要 `.lore/`）呢？**
A: 在 `.config.json` 里设 `mirror_targets: []`。`compress` 和 `mirror` 在文件系统上就是空操作；只有 `SUMMARY.md` 和 entry 文件生效。

**Q: 这跟 Cursor 的 `.cursorrules` 或 Aider 的 `AGENTS.md` 有什么不同？**
A: 那些是扁平的规则列表。lore 是结构化的（架构 / 决策 / 约定）、原子的（一条事实一个 entry）、有历史的（每条 entry 有 `#added` 和 `#verified` tag）。而且 lore 会替你生成这些文件。

**Q: lore 会调用 agent 的 API 吗？**
A: 不会。lore 是纯文件 I/O。调用 lore 的 agent 做语义工作（扫描代码、决定提取什么、分类变更）；lore 提供文件布局、ID 方案、标记规则和验证脚本。

**Q: agent 原生的 `/init` 或 `/compact` 呢？**
A: 它们用途不同。`/init` 是一次性项目扫描 → `CLAUDE.md`。`/compact` 压缩对话上下文。lore 的 `init` 和 `compress` 管长期项目知识，不是会话上下文。如果你在已经有非 lore `CLAUDE.md` 的项目上跑 `lore init`，接管检测（init step 0）会处理集成。

## 许可

本 skill 按原样提供。可自由使用、修改、定制以适应你的项目需求。