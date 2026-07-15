# lore 脚本

跨平台 Python 3.6+ 辅助脚本，减少重复的机械工作。无第三方依赖。被 `init` / `sync` / `audit` / `compress` / `lore mirror` 调用，也可独立运行做临时检查。

脚本清单和命令速查在仓库根 `README.md` 的"Scripts"章节里。本文件覆盖根 README 不适合放的内容：设计意图、集成点、局限。

## 设计要点

**优先跨平台。** 仅使用 Python 标准库，不依赖 `bash`、`jq` 或任何平台特定工具。Windows / Linux / macOS 行为完全一致。

**JSON 友好输出。** 每个脚本都支持 `--json` 便于机器消费。Agent 调用方解析输出；人类可以直接 `less` 或 `jq`（如果装了）。

**组合而非重复。** `find_duplicates.py`、`find_stale.py` 和 `history.py` 通过 `list_entries.py --json` 复用解析器，不重复实现 entry 格式解析。Entry 格式只在一处定义——将来格式变更只需改 `list_entries.py`。

**默认只读。** 这些脚本不写 `.lore/`，只观察。Agent 决定如何处理发现的问题。

**从项目根目录运行。** `list_entries.py` 向上遍历定位 `.lore/`。其他脚本通过 subprocess 调用它，所以这个约束会传递生效。

## 何时调用

| 脚本 | 调用点 | 用途 |
|---|---|---|
| `history.py` | lore history | 列出与 memory entry / file / scope 相关的 git commits；带 `--follow-superseded` 时沿 `#superseded-by` 链向前遍历 |
| `id_hash.py` | 写新 entry 时（init / sync）| 计算 entry ID 的 4 字符内容 hash |
| `list_entries.py` | query / audit / compress / history 的预步骤 | 把所有 entry 枚举为 JSON 供后续处理；当 entry 含 `#superseded-by` 时额外输出 `replaced_by` 字段 |
| `find_duplicates.py` | sync 步骤 5（去重）| 写之前找出可能的重复 entry |
| `find_stale.py` | audit 步骤 2；compress 步骤 2；lore mirror（可选）| 找出过期 entry 或已标记 `#stale` 的 entry；按 `#superseded-by` 目标对 pending-review 分组，并报告 `BROKEN_CHAIN` 孤儿 |

## 输出通道

**stdout 是数据通道；stderr 是警告通道。** 所有脚本遵循这个分离，这样 `--json` 消费者就不必从解析结果里过滤噪音。当前只有 `list_entries.py` 会发警告：

- `[WARN] .lore/.config.json has no schema_version field.` —— 配置文件存在但缺 `schema_version` 字段时，每个调用触发一次。加 `"schema_version": 1` 即可消除。
- `[WARN] .lore/.config.json#schema_version=N is newer than this lore skill expects (max: 1).` —— 配置版本超过本 skill 能理解的范围时触发。从上游 pull 最新 lore。

两条警告都是告知性质；`list_entries.py` 不管配置状态如何，stdout 输出始终一致。完整 schema 版本策略见 `references/compatibility.md`。

## 测试

没有真实 `.lore/` 时，可以快速验证 import 和参数解析是否正常：

```bash
python scripts/id_hash.py "test entry"
python scripts/list_entries.py   # 应输出 "(no entries)" 或清晰报错
```

`list_entries.py`、`find_duplicates.py`、`find_stale.py` 需要有内容的 `.lore/` 才能产出有意义的输出。先用 `lore init` 建一个。

## 局限

- **去重只到词袋重叠程度。** Jaccard 相似度能抓到词汇相似的改写，但抓不到语义等价（如 "use TypeScript" vs "TypeScript-only codebase"）。更深的检查仍需 LLM 介入。
- **日期计算比较朴素。** `find_stale.py` 直接用 `#verified` / `#added` 标签的日期。如果系统时钟不对，结果会偏差。
- **不自动 archive。** 脚本会报告带 `#stale` tag 的 entry 和坏链，但不会移动或删除任何东西。过期的 entry 留在原 scope 文件、带 `#stale` tag；git 历史保留全部。
- **理论上可能有 hash 冲突**（4 个十六进制字符 = 16 位 = 1/65536 概率）。实际项目基本不会遇到。如果遇到了，对 entry 文本做微调以改变 hash。