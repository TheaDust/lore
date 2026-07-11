# 工作流参考

七个 lore 工作流的详细参考。[`SKILL.md`](../SKILL.md) 给一段式摘要；本文给出每个工作流的完整程序、输出、edge cases 与相关文档。

## 两层 trigger 模型

skill 有两个不同的 trigger 表面：

**Tier 1 —— skill 加载。** 由 frontmatter description 控制。只有当用户显式调用 `lore <cmd>` 或直接叫出 skill 名字（"lore"、"memory bank"、"project memory"）时才会加载。裸的 "init" / "compress" / "initialize" 推迟给 agent 原生命令。

**Tier 2 —— 内部提案。** skill 在本 session 加载后，某些命令有内部阈值用于主动提案：

| 命令 | 隐式 trigger | 给用户的输出 |
|---|---|---|
| `sync` | ≥50 行 / 跨 ≥2 个目录；或新 module / dir / dep；或对话里出现新约定 | marker 提案（NEW / STALE / REFINED） |
| `compress` | entries > 500；或 SUMMARY 缺失；或上次 compress > 30 天 | 在 sync 提案末尾追加 `[COMPRESS NOTICE]` |
| `audit` | sync 过程中检测到冲突 | sync 输出里的 `[ALERT]` marker |
| `mirror` | `compress` 流程中若 `auto_mirror: true` | 静默写（或 false 时逐 target 询问） |

`init`、`query`、`history` **始终显式** —— 需要用户意图。

---

## `init` —— 初始化 memory bank

**Trigger**：仅显式（`lore init`）

**适用场景**：新项目首次用 lore；或老项目接入 lore 且已有平台文件（`CLAUDE.md`、`AGENTS.md` 等）。

### 程序

1. 检查 `.lore/` 是否存在。
   - 不存在 → 创建 `.lore/` 并写入带默认值的初始 `.config.json`
   - 存在 → 加载已有 config（缺字段用默认值）
2. 用 [`platform-mirrors.md`](platform-mirrors.md) 中的候选清单扫描 repo 根目录的现有平台文件
3. 对每个检出的文件分类：
   - **(a)** 已是 lore mirror —— 含 `## Lore` section → 接管，替换 Lore 段
   - **(b)** 用户手写 —— 含 `## My notes` 但无 `## Lore` → 整文件保留；问用户
   - **(c)** 无标记 —— 两者都没有 → 问用户（preserve / take over / abort）
4. 没检出任何平台文件：多选 agent 列表（Claude Code / Cursor / Cline / Aider / OpenCode 等），把 `mirror_targets` 写进 config
5. 决定 scope：monorepo → 用 [`monorepo-detection.md`](monorepo-detection.md) marker；单 package → 只用 `_global/`
6. 创建 `.lore/{_global/, scopes/<scope>/}` 空 layer 文件
7. 为新创建的 target 生成 platform mirror（完整两段模板）

### 输出

- 完整 `.lore/` 目录树
- 更新过的平台 mirror 文件（含 `## Lore` + `## My notes` 段）
- 落盘的 `.lore/.config.json`（含 `mirror_targets`、`schema_version: 1`、默认值）

### Edge cases

- **已有的非 lore `CLAUDE.md`** → 走 takeover 流程；用户现有内容变 `## My notes` 段
- **混合平台文件**（如同时有 `CLAUDE.md` 和 `AGENTS.md`）→ 每个文件各自获得 Lore 段
- **无 git 仓库** → `init` 可用，但后续 `sync` 和 `history` 需要 git
- **Monorepo 有重叠 scope**（如 frontend 和 src/ 同时存在）→ 问用户哪个是 canonical

### 相关文档

- [`monorepo-detection.md`](monorepo-detection.md) —— scope 识别规则
- [`platform-mirrors.md`](platform-mirrors.md) —— 各平台文件映射、两段结构
- [`config.md`](config.md) —— `.config.json` schema

---

## `sync` —— 代码变更后更新

**Trigger**：
- **显式**：用户说 `lore sync`
- **隐式提案**：≥50 行 / 跨 ≥2 个目录；或新 module / dir / dep；或对话里出现新约定

**适用场景**：完成 feature、refactor、依赖变更、新约定。始终 opt-in —— `sync` 永远不会自己跑（要么有提案，要么用户显式调用）。

### 程序

1. **compress 阈值检查（静默）**：
   - entries > 500 → `[COMPRESS NOTICE]`（不阻塞，可推迟）
   - `SUMMARY.md` 缺失 → `[COMPRESS NOTICE]`
   - 上次 `Last compressed:` > 30 天 → `[COMPRESS NOTICE]`
2. **从 `git diff` 检测 delta**（committed 或 working tree），并重扫新增文件
3. **文件 → scope 映射**：`frontend/src/...` → `scopes/frontend/`；跨 scope（root config、顶层依赖）→ `_global/`
4. **分类每个变更**：
   - 新 module / dep / 文件结构 → `[ARCHITECTURE.md]`
   - 新「我们选了 X 因为 Y」→ `[DECISIONS.md]`
   - 新「我们不用 Z」→ `[CONVENTIONS.md]`
   - 现有 entry 被矛盾 → `[STALE]`（保留，追加 `#stale:<today>`）
   - 现有 entry 文本需要小幅更新 → `[REFINED]`（保留 ID，更新 `#verified:<today>`）
5. **输出提案**：每个 marker 类型一节
6. **用户接受 / 拒绝**：按 marker（或全局）
7. **应用接受的变更**：append `[NEW]`、追加 `#stale:` tag、或原地替换 `[REFINED]` 文本

### 输出

更新过的 `.lore/*.md` 文件。若 `[COMPRESS NOTICE]` 触发，会附加在提案末尾。

### Edge cases

- **纯 typo fix、lockfile 变更、README 改写、< 30 行的微调** → **不要**提议 sync（噪声）
- **`sync` 不会更新 platform mirror** —— 那是独立的 `mirror` 命令。理由：保持 agent 端文件的 `git log` 可读
- **sync 过程中的冲突** → 输出 `[ALERT]`；由用户解决
- **`sync_updates_mirror: true` in config** → 恢复旧行为（每次 sync 都更新 mirror），代价是 `git log` 噪声

### 相关文档

- [`stale-new-markers.md`](stale-new-markers.md) —— marker 完整规范和回复语义
- [`entry-format.md`](entry-format.md) —— `#added` / `#verified` / `#stale` tag 语义
- [`config.md`](config.md#sync_trust) —— `sync_trust: low | medium | high` 控制自动 vs 提示接受

---

## `query` —— 从 memory 里查答案

**Trigger**：仅显式（`lore query <term>` 或 `lore query <scope>:<term>`）

**适用场景**：session 开始、调试、onboarding、问「为什么」、写可能跟现有 entry 冲突的代码。

### 程序

1. 读 `.lore/SUMMARY.md` 当目录
2. 对 entry 文本和 ID 做模糊匹配
3. 可选地深入到具体 scope 文件拿更完整上下文
4. 返回命中的 entry，带稳定 `[file#ID]` 引用和一行摘要

### 输出

bounded 命中 entry 列表：

```
[_global/DECISIONS.md#DEC-2026-07-11-6137] Picked OpenAI-compatible LLM API
[scopes/backend/CONVENTIONS.md#CONV-2026-07-11-9b89] Embedding has two backends
```

`[file#ID]` 引用让 agent `cat` 文件对应行拿完整文本。

### Edge cases

- **没 `SUMMARY.md`** → 直接扫所有 `.lore/*.md`
- **空 term** → 整段返回 `SUMMARY.md`（相当于目录列表）
- **term 太宽** → 可能返回大量 entry；考虑用 `<scope>:<term>` 缩小
- **query 命中 `[STALE]` entry** → 仍会返回，`[STALE]` 标记在 agent 上下文里可见

### 相关文档

- [`entry-format.md`](entry-format.md) —— ID 格式、scope 约定
- [`summary-template.md`](summary-template.md) —— `SUMMARY.md` 的内容

---

## `audit` —— 检查 memory 跟现实是否一致

**Trigger**：
- **隐式**：sync 过程中检测到冲突时输出 `[ALERT]`（见 SKILL.md 的 Conflict Resolution）
- **显式**：`lore audit` 做周期性体检

**适用场景**：季度 review、大重构前、怀疑有 stale entry、把 lore 给新贡献者前。

### 程序

1. 跑 `python scripts/find_stale.py --days=90 --json` 找 `#added` > 90 天且无 `#verified` 的 entry
2. 跑 `python scripts/find_duplicates.py --json` 找内容冲突
3. 交叉检查 entry 引用的代码路径（`[file#ID]` 引用里包含的路径）跟当前文件系统
4. 按问题类型分组输出 `[ALERT]` 报告

### 输出

```
[ALERT] 5 entries may be stale (no #verified in >90 days):
  - ARCH-2026-01-15-d7a3  last verified 2026-04-12
  ...

[ALERT] 2 entries contradict current code:
  - CONV-2026-03-01-1f8c  says "use webpack"; project now uses Vite
```

### Edge cases

- **首次 audit（刚 init 完）** → 会有很多 old entry 显示 stale，正常
- **大项目（500+ entry）** → 报告可能很长；考虑 scope
- **`audit` 不修改文件** —— 纯观察。要落地整改，跑 `sync` 走提案-接受流程

### 相关文档

- [`stale-new-markers.md`](stale-new-markers.md) —— stale entry 怎么标
- [`compatibility.md`](compatibility.md) —— 什么时候该归档老 entry

---

## `compress` —— 重建顶层 summary

**Trigger**：
- **隐式**：sync 过程中 `[COMPRESS NOTICE]`（entries > 500 / SUMMARY 缺失 / 上次 compress > 30 天）
- **显式**：`lore compress`

**适用场景**：`SUMMARY.md` 过期、想要新目录、大批 sync 之后、分享 lore 前。

### 程序

1. 跑 `python scripts/list_entries.py --json` 枚举所有 entry
2. 可选地跑 `python scripts/find_stale.py --json` 标记不该出现在 summary 里的 entry（recently-stale 或 long-unverified）
3. 对每个 `(scope, layer)` 对，按 [`summary-template.md`](summary-template.md) 的挑选规则选 3–5 条最重要的 entry
4. 按模板写 `SUMMARY.md`
5. **停。** compress 本身只写 `SUMMARY.md`。底层 ARCHITECTURE / DECISIONS / CONVENTIONS 文件**完全不动**
6. **Mirror 重生成**（如果 config 里 `auto_mirror: true`）：对每个 `mirror_targets` entry 写入对应平台文件，做 content-based dedup。若 `auto_mirror: false`，逐 target 询问用户

### 输出

- 更新过的 `.lore/SUMMARY.md`
- （可选）更新过的平台 mirror 文件

### 幂等性

compress 幂等：跑两次产出同样的 `SUMMARY.md`（日期戳除外）。在新的 sync 之后再跑会自动收录新 entry。

### Edge cases

- **自动 mirror 写入** 做 content-dedup —— 与现有文件 byte-identical 就 no-op
- **My notes 段** 在 mirror 写入时永远保留
- **compress 永不删 entry** —— 只写 `SUMMARY.md`
- **没有 entry** → 写空 `SUMMARY.md`，`Total entries: 0`

### 相关文档

- [`summary-template.md`](summary-template.md) —— 挑选规则、模板
- [`platform-mirrors.md`](platform-mirrors.md) —— mirror 写入语义

---

## `mirror` —— 重生成平台 mirror

**Trigger**：
- **隐式**：`compress` 流程中若 `auto_mirror: true`
- **显式**：`lore mirror`

**适用场景**：一批 sync 完想同步到 agent 端文件、手改过 `.lore/*.md` 想同步到 mirror、验证 mirror 没漂移。

### 程序

1. 读当前 `.lore/SUMMARY.md` 和 scope-tagged 索引
2. 对每个配置的 `mirror_targets` entry，读现有文件并检测段边界（`## Lore` / `---` / `## My notes`）
3. 计算新 Lore 段内容（index mode 下约 500 字节）
4. **Content-based dedup**：若新 Lore 段跟现有 byte-identical，跳过写。报 "No changes needed: `<file>`"
5. 替换 Lore 段（整段重写，不与旧内容合并）。My notes 段原样保留
6. 写回文件。报 "Mirror updated: `<file>`"

### 输出

更新过的 `CLAUDE.md` / `AGENTS.md` / `.cursorrules` / `.clinerules` 等，或没变化时给出 no-op 报告。

### Edge cases

- **文件含 `## Lore` + `---` + `## My notes`** → 标准接管，只换 Lore 段
- **文件含 `## My notes` 但无 `## Lore`** → 整文件视为用户 notes，skill **不写**。sync 想重组文件前需用户确认
- **文件两者都没有** → 整文件视为 Lore（暂无 My notes 段）。下次 mirror 追加 `---` + 空 My notes 段
- **文件不存在** → 用完整两段模板创建
- **Content-dedup 按 target** —— 一个 target 跳过不影响另一个写

### 相关文档

- [`platform-mirrors.md`](platform-mirrors.md) —— 各平台完整规则、两段结构、My notes 语义
- [`stale-new-markers.md`](stale-new-markers.md) —— sync 何时提议 mirror 变化

---

## `history` —— 列出与 memory entry 相关的 git commits

**Trigger**：仅显式（`lore history <entry-id>|<file-path>|--scope=<name>`）

**适用场景**：查「这条 entry 为什么存在」、调试、onboarding、查文件什么时候改过。

### 程序

三种形式（按参数类型 dispatch）：

| 形式 | 触发 | 行为 |
|---|---|---|
| Entry | `[LAYER-DATE-HASH]` | 在 `.lore/` 里定位该 entry，导出 `#added` 日期和引用的代码文件，跑 `git log --since=<date>` |
| File | 含 `/` 或以 `.` 开头 | 对给定路径跑 `git log --since=1970-01-01` |
| Scope | 仅 `--scope=<name>` | 对 `.lore/scopes/<name>/` 下每个 `*.md` 跑 file 形式（在该 lore 文件路径本身上） |

可选 `--since=YYYY-MM-DD` 覆盖日期过滤。可选 `--json` 切到机器可读输出。

### 输出

Markdown（默认）或 JSON：

```markdown
# history: [DEC-2026-02-03-7c19]

  abc1234  2026-05-12  refactor: extract chat agent_loop (#87)
  def5678  2026-03-08  feat: switch chat chain to chat_fast (#74)
```

### Edge cases

- **非 git 仓库** → 报错：`lore history requires git; not a git repository`
- **entry 没有 `#added` tag** → stderr 警告，用全量历史（`--since=1970`）
- **`--since=YYYY-MM-DD` 在 +0800 时区且当天有 commits** → 可能返回 0（git 按 UTC 过滤）；workaround：用 `--since=YYYY-MM-DD T00:00:00` 或选前一天
- **entry 引用的文件已不存在** → 仍能找到 entry；该文件的 `git log` 可能为空

### 相关文档

- [`history-command.md`](history-command.md) —— 完整规范、dispatch 规则、错误码

---

## 跨工作流笔记

### 典型调用序列

```
init
  ↓
[sync ⇄ query ⇄ audit]   ← 这三个可互换；agent 按上下文挑选
  ↓
compress                 ← 当 SUMMARY.md 过期时
  ↓
mirror（或 compress 时 auto_mirror: true 自动）
```

### 谁写什么

| 文件 | 谁写 |
|---|---|
| `.lore/SUMMARY.md` | `compress` |
| `.lore/{_global,scopes/<scope>}/<LAYER>.md` | `sync`、手动编辑 |
| `.lore/.config.json` | `init`、手动编辑 |
| `<project-root>/<platform files>` | `init`、`mirror`、`compress`（若 `auto_mirror: true`） |

### 永不静默发生的事

- 文件变更 —— `sync` 出提案，用户接受/拒绝
- 每次 `sync` 都重写 platform mirror（设计故意，单独命令）
- `compress` 删 entry（只写 SUMMARY.md）
- 把 entry 标 `[STALE]` 不出提案
- `init` 不打招呼就覆盖用户手写的 `CLAUDE.md`

### Helper 脚本位置

所有 Python helper 在 `scripts/`：

| 脚本 | 谁用 |
|---|---|
| `id_hash.py` | `init`、`sync`、手动创建 entry |
| `list_entries.py` | `compress`、`audit` |
| `find_stale.py` | `audit`、`compress` |
| `find_duplicates.py` | `audit` |
| `history.py` | `history` |
| `migrate.py`（v1 未发布，规划中）| schema_version bump 时 |