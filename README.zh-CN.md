# lore

<p align="center">
  <img src="docs/lore-poster.svg" alt="lore" width="640">
</p>

<p align="center">
  <a href="https://github.com/TheaDust/lore"><img src="https://img.shields.io/github/stars/TheaDust/lore?style=flat&label=stars" alt="stars"></a>
  <a href="https://github.com/TheaDust/lore/commits/main"><img src="https://img.shields.io/github/last-commit/TheaDust/lore?style=flat&label=last%20commit" alt="last commit"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="license"></a>
  <img src="https://img.shields.io/badge/python-3.6%2B-blue.svg" alt="python">
</p>

<p align="center"><em><strong>lore</strong>（名词）—— 某一主题的传统与知识，由人口口相传。</em></p>

<p align="right">中文 · <a href="README.md">English</a></p>

> 框架无关的 AI 编程智能体项目记忆。长期保存架构、决策与约定为纯 Markdown，任何智能体都能读取。

> 当下痛点：`/init` 后，平台记忆文件往往懒得手动更新，过时知识污染记忆。Claude 读 `CLAUDE.md`，Codex 读 `AGENTS.md`，两者逐渐漂移 ... ... 
>
> 于是 `lore` 应运而生。

| 结构化 | 可检索 | 可移植 |
|---|---|---|
| `.lore/` 内按 ARCH / DEC / CONV 分层，条目带稳定 ID 与生命周期标签 | `lore query` 以 `[file#ID]` 引用回答；`lore history` 追溯 git 提交 | 单一事实源 `.lore/` 投影到 `CLAUDE.md` / `.cursorrules` / `AGENTS.md` |

> **lore 是 SKILL，不是 CLI。** 它是一份 Markdown 规范（[`skill/SKILL.md`](skill/SKILL.md)），供 Claude Code、Cursor、OpenCode、Cline、Aider、Copilot 等读取。没有 `lore` 二进制文件——`lore init` / `lore sync` 是对智能体说的话。

> 目录：[安装](#安装) · [快速上手](#快速上手) · [工作原理](#工作原理) · [七个工作流](#七个工作流) · [平台 Mirror](#平台-mirror) · [FAQ](#faq)

## 安装

**通过 `skills` CLI（推荐）：**

```bash
npx skills add https://github.com/TheaDust/lore --skill lore -y          # 项目级：./.agents/skills/lore
npx skills add https://github.com/TheaDust/lore --skill lore -g -y       # 全局：~/.agents/skills/lore
# 只装给指定 agent：
npx skills add https://github.com/TheaDust/lore --skill lore -g -y --agent claude-code
npx skills add https://github.com/TheaDust/lore --skill lore -g -y --agent opencode
```

**手动安装：**安装单元是 `skill/`：

```bash
git clone https://github.com/TheaDust/lore.git /tmp/lore
cp -r /tmp/lore/skill <你的-agent-skills-目录>/lore
# 例如 cp -r /tmp/lore/skill ~/.claude/skills/lore
```

或直接告诉智能体：

> 从 https://github.com/TheaDust/lore 安装 skill（skill 在 `skill/` 子目录）。

完整参考文档：[`skill/references/`](skill/references/) · 工作流平实说明：[`WORKFLOWS.zh-CN.md`](WORKFLOWS.zh-CN.md)

## 快速上手

对智能体说的话（无二进制）：

显式 `lore <command>` 和明确针对项目记忆的自然语言请求（例如“记住这个项目决策”）都可以触发。原生 `/init` / `/compact` 和无关的通用任务不会触发 lore。

```bash
lore init      # 一次性：扫描项目、起草条目、确认后创建 .lore/
lore sync      # 功能或重构后：检测变更、提议 [NEW]/[STALE]/[REFINED]/[ALERT]
lore compress  # 刷新 SUMMARY.md（按 auto_mirror 决定是否更新 mirror）
lore mirror    # 强制用当前 .lore/ 重写 CLAUDE.md 等 mirror 文件
```

```bash
lore query <关键词>                    # 从记忆回答并引用 ID
lore audit                             # 检查记忆与现实偏差，报告写入 .lore/audit/
lore history <entry-id|路径|--scope> [--json]  # 展示相关 git 提交
```

## 工作原理

### 布局 — `.lore/` 里有什么

```
.lore/
├── SUMMARY.md              # 摘要，新智能体先读它
├── .config.json            # 可选配置
├── _global/                # 全局记忆
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   └── CONVENTIONS.md
├── scopes/<scope>/         # 每个作用域的记忆，如frontend，backend等
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   └── CONVENTIONS.md
├── draft/                  # init 草案
├── audit/                  # audit 报告
└── .archive/               # mirror 清空时的 My notes 备份
```

### 条目格式 — 一条事实一个 bullet

每条 entry 为一条 bullet，最多两行，带确定性 ID `LAYER-YYYY-MM-DD-xxxx` — `xxxx` 是条目文本的 4 位十六进制 hash，重写同一事实会得到同一 ID：

```markdown
- [ARCH-2026-07-09-a3f2] Use Next.js App Router; reason: streaming + RSC. #added:2026-07-09
- [DEC-2026-02-03-7c19] Chose Zustand over Redux; reason: 60% less boilerplate. #added:2026-02-03 #verified:2026-06-15
- [CONV-2026-01-20-b1e8] Never commit secrets; use dotenv + .env.local. #added:2026-01-20
```

修改条目文本会改变 ID — 旧 ID 只存在于 git 历史中。生命周期标签（`#added` / `#verified` / `#stale`）记录条目状态；`#superseded-by:<id>` 串联替换链，供 `compress` / `history` 追溯。规范见 [`skill/references/entry-format.md`](skill/references/entry-format.md)。

查询当前状态和生成摘要时，会排除带 `#stale` 或 `#superseded-by` 的条目，即使它没有后继条目。无标签条目仍可使用；日期久远只是复查信号。历史问题仍可读取失效条目，但会明确说明其状态。

ARCH 记录架构事实，可以在两行限制内附带简短理由。方案比较、权衡或需要独立条目展开的详细理由归入 DEC；仅出现 `reason:` 不会强制拆分。

### 写工作流 — `init`、`sync`、`compress`、`mirror`

七个工作流中有四个会写入 `.lore/`或平台记忆文件：

- **`init`** — 一次性初始化。扫描项目，把候选条目起草到 `.lore/draft/`，询问要覆盖哪些智能体的 mirror 文件；确认后创建 `.lore/`（先跑一次 `compress` 生成 `SUMMARY.md`）及 mirror 文件。
- **`sync`** — 每个功能、重构或 bug 修复后运行。合并上次 sync 以来的提交与 `git diff HEAD` 中已暂存、未暂存的改动，另行扫描未跟踪文件（空仓库采用文件扫描）。写入前传入每条候选正文检查重复，把事实归类为 ARCH / DEC / CONV，提议 `[NEW]` / `[STALE]` / `[REFINED]` / `[ALERT]` 更新。低风险变更按 sync 信任级别自动应用，新增或矛盾之处等你确认。只写 `.lore/*` ，默认不改写 mirrors。
- **`compress`** — 当 `SUMMARY.md` 过期时重建摘要（每个 scope 每层 3–5 条，幂等），`auto_mirror` 开启时一并重生成 mirrors。
- **`mirror`** — 用当前 `.lore/` 强制重写 `CLAUDE.md` 等 mirror 文件，Lore 段未变化的 target 跳过，`My notes` 原样保留。

**典型节奏：** `lore init` 一次 → 每个功能/重构后 `lore sync` → `SUMMARY.md` 过期时 `lore compress` → scope改变或需要发布时 `lore mirror`。

mirror 把约 600 字节的索引投影到智能体本就会读取的文件中，保持每次会话成本恒定：

<details>
<summary>示例 <code>CLAUDE.md</code> Lore 段</summary>

```markdown
<!-- LORE:START -->
## Lore (auto-managed)

Project memory at `.lore/`. Before project-specific questions, read `.lore/SUMMARY.md`
as the digest, then open the referenced entries for the full text; cite entry IDs.

**Structure**:
- Digest: `.lore/SUMMARY.md`
- Global: `.lore/_global/`
- Scopes: `.lore/scopes/`
  - `.lore/scopes/backend/` (Flask 3 + SQLAlchemy 2 + pytest; Python 3.11+)
  - `.lore/scopes/frontend/` (React 18 + TypeScript + Vite + Zustand + Axios)

**Query**: `lore query <term>` or `lore query <scope>:<term>`
<!-- LORE:END -->
---
## My notes (free edit)
- 这里的内容每次同步都会原样保留。
```

</details>

其余三个 — `query`、`audit`、`history` — 只读，详见 [七个工作流](#七个工作流) 表格。

## 七个工作流

| 命令 | 作用 | 写入 | 参考 |
|---|---|---|---|
| `init` | 扫描项目、起草条目、确认 | `.lore/*` + mirrors | [workflows#init](skill/references/workflows.md#init--initialize-the-memory-bank) |
| `sync` | 检测变更、提议更新 | 仅 `.lore/*` | [workflows#sync](skill/references/workflows.md#sync--update-after-a-change) |
| `query` | 从记忆回答并引用 ID | 无 | [workflows#query](skill/references/workflows.md#query--answer-from-memory) |
| `audit` | 检查记忆与现实、写报告 | 仅 `.lore/audit/*` | [workflows#audit](skill/references/workflows.md#audit--check-memory-vs-reality) |
| `compress` | 重建 `SUMMARY.md` | `.lore/SUMMARY.md` | [workflows#compress](skill/references/workflows.md#compress--build-the-top-level-summary) |
| `mirror` | 重生成 mirrors（去重） | `CLAUDE.md` 等 | [workflows#mirror](skill/references/workflows.md#mirror--regenerate-platform-mirrors) |
| `history` | 展示相关 git 提交 | 无 | [workflows#history](skill/references/workflows.md#history--show-git-commits-related-to-a-memory-entry) |

<details>
<summary>Sync 信任级别</summary>

| 变更类型 | `high` | `medium`（默认） | `low` |
|---|---|---|---|
| 去重命中 | 自动 | 自动 | 确认 |
| REFINED 仅改标签 | 自动 | 自动 | 确认 |
| REFINED 改正文 | 自动 | 确认 | 确认 |
| `NEW` 条目 | 自动 | 确认 | 确认 |
| `STALE` 标记 | 自动 | 确认 | 确认 |
| `ALERT` | 确认 | 确认 | 确认 |

`medium` 自动处理低风险变更，新增或矛盾需确认。

</details>

## 平台 Mirror

事实源是 `.lore/*`，mirrors 是投影到智能体已读取的文件。targets 自动检测（扫描仓库根）；未检测到时 `lore init` 多选询问，或在 `.lore/.config.json` 中显式配置 `mirror_targets`。

| 平台 | 文件 |
|---|---|
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursorrules` / `.cursor/rules/*.mdc` |
| Cline | `.clinerules` |
| Aider / Codex / OpenCode | `AGENTS.md` |
| Windsurf | `.windsurfrules` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Continue.dev | `.continue/rules/lore.md` |
| LangGraph / DeepAgents | 无文件 — 直接读 `.lore/*.md` |

每个 mirror 以 `---` 分隔为 `## Lore (auto-managed)`（`<!-- LORE:START -->` / `<!-- LORE:END -->` 包裹）与 `## My notes (free edit)`（原样保留）。

<details>
<summary>Token 成本</summary>

| 组件 | 何时加载 | 典型大小 | 每次会话 |
|---|---|---|---|
| Mirror 文件 | 每次会话 | 约 600 字节（index 模式） | 是 |
| `skill/SKILL.md` | 每次 `lore <cmd>` | 约 19 KB | 按调用 |
| `skill/references/workflows.md` | 每次 `lore <cmd>`（仅路由段） | 约 17 KB | 按调用 |
| `.lore/SUMMARY.md` | 按需 | 1–30 KB | 按需 |
| `scopes/<scope>/*.md` | 按需 | 1–5 KB 各 | 按需 |
| `lore query` 结果 | 按查询 | 按命中条数 | 按查询 |

Mirror 大小随 scope 数量变化，与条目数无关。不建议将 `SUMMARY.md` 完整塞入 mirror。

</details>

<details>
<summary>脚本与测试</summary>

```bash
python skill/scripts/id_hash.py "Use Next.js App Router"      # 4 字符 ID hash
python skill/scripts/list_entries.py --json
python skill/scripts/find_duplicates.py --json
python skill/scripts/find_duplicates.py --json --candidate "Use Next.js App Router"
python skill/scripts/find_stale.py --days=90 --json
python skill/scripts/history.py DEC-2026-02-03-7c19
```

Python 3.6+，仅标准库。测试：`python -m unittest discover -s tests -v`。详见 [`skill/scripts/README.md`](skill/scripts/README.md)。

</details>

<details>
<summary>配置</summary>

`.lore/.config.json` 可选：

```json
{
  "schema_version": 1,
  "auto_mirror": false,
  "sync_updates_mirror": false,
  "sync_trust": "medium",
  "mirror_targets": ["CLAUDE.md"],
  "mirror_mode": "index",
  "compress_thresholds": { "max_entries": 500, "max_days_since_compress": 30 },
  "sync_thresholds": { "min_lines_changed": 50, "min_directories_changed": 2 }
}
```

见 [`skill/references/config.md`](skill/references/config.md) 与 [`skill/references/compatibility.md`](skill/references/compatibility.md)。

</details>

<details>
<summary>不适用场景</summary>

- 短命脚本或一次性 demo
- 决策每周变化的快速原型
- 微型单文件项目
- 希望智能体只读的项目
- 50+ packages 的超大 monorepo（建议按集群拆分）

</details>

## FAQ

<details>
<summary>不在 git 仓库能用吗？</summary>

大部分能。`init` / `query` / `audit` / `compress` / `mirror` 直接读文件即可。`sync` 失去 `git diff`（智能体会询问改了什么），`history` 需要 git 仓库。辅助脚本两种情况都能用。

</details>

<details>
<summary>能直接手改 <code>.lore/*.md</code> 吗？</summary>

可以 — 纯 Markdown。新增条目用 `id_hash.py` 算 ID。改完跑 `lore mirror` 刷新 mirrors。

</details>

<details>
<summary>与 <code>.cursorrules</code> / <code>AGENTS.md</code> 有什么不同？</summary>

它们是扁平规则列表。lore 是结构化（ARCH/DEC/CONV）、原子化（一条事实一条 entry）、带历史（`#added` / `#verified` / `#stale`）的记忆库，并替你生成这些文件。

</details>

<details>
<summary>与智能体原生的 <code>/init</code> / <code>/compact</code> 冲突吗？</summary>

用途不同 — `/init` 搭架子，`/compact` 压上下文，lore 管长期知识，三者共存。

</details>

<details>
<summary>已有根 <code>AGENTS.md</code> 还能用 lore 吗？</summary>

跑 `lore init` 选接管 — 原文件变为两段 mirror，原内容原样保留为 `My notes`。`CLAUDE.md` / `.cursorrules` 同理。

</details>

<details>
<summary><code>init</code> 后新增 scope 要重跑吗？</summary>

不用 — `lore sync` 会从变更路径检测新 scope 并自动创建 `scopes/<name>/`，再 `lore mirror` 即可。

</details>

<details>
<summary><code>sync</code> 与 <code>mirror</code> 区别？</summary>

`sync` 根据代码更新 `.lore/`；`mirror` 根据 `.lore/` 更新智能体侧文件。`sync` 故意不碰 mirrors，`git log` 更清晰。

</details>

<details>
<summary>不同意某条 entry 怎么办？</summary>

直接编辑 `.lore/*.md`。下次 `mirror` / `compress` 生效。`git checkout .lore/` 可回退。

</details>

<details>
<summary>不用 git 多机同步 <code>.lore/</code> 可以吗？</summary>

推荐 git。其他同步工具对纯文本可行，但不懂 ID 与标签。不要两个智能体同时写同一 `.lore/`。

</details>

## 许可

[MIT](./LICENSE)

---

<p align="center">
  <a href="skill/SKILL.md">skill/SKILL.md</a> ·
  <a href="skill/references/workflows.md">workflows</a> ·
  <a href="skill/references/entry-format.md">entry-format</a> ·
  <a href="skill/references/summary-template.md">summary-template</a> ·
  <a href="skill/references/audit-template.md">audit-template</a> ·
  <a href="skill/references/monorepo-detection.md">monorepo-detection</a> ·
  <a href="skill/references/stale-new-markers.md">stale-new-markers</a> ·
  <a href="skill/references/platform-mirrors.md">platform-mirrors</a> ·
  <a href="skill/references/config.md">config</a> ·
  <a href="skill/references/history-command.md">history-command</a> ·
  <a href="skill/references/compatibility.md">compatibility</a> ·
  <a href="skill/scripts/README.md">scripts</a>
</p>
