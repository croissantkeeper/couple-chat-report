# couplechat

把两个人的聊天导出，变成一份有数据依据、由大模型执笔的报告。

每对情侣的情况都不一样：有人异地跨时区，有人同城；有人常出差，有人不打电话。这个项目把“这对情侣的情况”“通用的统计方法”和“怎么讲故事”分成三层，换一对情侣只需要换一份配置。

## 设计

```
导出文件 ──ingest──▶ 统一消息表 ──analyses（九个功能组）──▶ facts.json + 图件 + 表格
                                                          │
profile.yaml（称呼、行程、节点、背景、文风）──────────────┤
                                                          ▼
                                   story：提故事线 ▶ 写正文 ▶ 审稿
                                                          ▼
                                   render：填入数字、检查 ▶ report.md
```

- **profile**（`profiles/*.yaml`）：因人而异的一切。两人的显示名、每人的行程与时区、关系节点、自定义词表、当事人补充的背景、文风。
- **ingest**（`src/couplechat/ingest/`）：每种导出格式一个适配器，输出统一的消息表。后面的代码只认这张表。
- **analyses**（`src/couplechat/analyses/`）：按功能分成九组，每组负责自己的数字、图件和表格，只计算，不解读。每组先判断自己是否适用于这对情侣；同城情侣会得到“时差：未启用”，而不是报错。
- **facts.json**：报告可以引用的全部数字，每个数字有编号和口径说明。格式见 [docs/facts-schema.md](docs/facts-schema.md)。
- **story**（`src/couplechat/story/`，提示词在 `prompts/`）：三次模型调用。先提出两三条候选故事线，由你挑选；再按选定的故事线写正文；最后审稿。
- **render**（`src/couplechat/render/`）：把占位符换成数字，并检查正文里有没有手写的数字。

### 数字不由模型书写

模型写正文时不直接写数字，只写占位符，例如 `共发出 {{volume.text.A}} 条文字`，由渲染程序填入。这样数字不会被编造，重新统计后正文也不必重写。`render` 会标出未知的编号和手写的多位数字。

## 九个功能组，27 张图

| 功能组 | 回答的问题 | 图件 | 适用条件 |
|---|---|---|---|
| `volume` 聊天量与对称性 | 聊了多少、谁说得多、用什么媒介 | 每日趋势、月度分布、逐周占比、日历、消息类型、单条长度与每日字数 | 总是 |
| `rhythm` 作息节奏 | 各自在一天、一周的什么时候聊 | 星期×小时、逐周小时分布、小时均值与波动、深夜比例 | 总是 |
| `timezones` 两套时钟 | 两人在各自一天的什么时候相遇 | 双时钟对照、时差变化前后 | 时钟不同的天数足够多 |
| `sessions` 会话与回应 | 谁先开口、聊多久、接话多快 | 会话形态、会话发起、接话节奏、完整等待分布 | 总是 |
| `language` 语言 | 各自的口头禅、共同的词 | 词云、共同高频词、特征词、完整短句、词组逐周出现率 | 总是（内容敏感） |
| `greetings` 问候 | 早安晚安按谁的时间发、怎样被接住 | 问候的双时钟分布、问候配对与晚安方向 | 匹配到足够多的问候 |
| `relationship` 关系阶段 | 关系节点前后有什么变化、最近怎样 | 阶段时间线、近期等长窗口对照 | profile 有关系节点；天数足够 |
| `calls` 通话 | 文字之外有多少通话 | 逐周通话事件 | 导出里有通话事件 |
| `itinerary` 行程 | 聊天量是否随所在城市起伏 | 行程与聊天量 | profile 有多段行程 |

每张图的编号和说明见 [docs/figures.md](docs/figures.md)。统计表输出在 `output/tables/`。

## 隐私

聊天记录属于两个人。使用前请确认双方都同意。

- **默认只把聚合统计发给模型。** 原始消息不离开本机；发送内容由 `facts.llm_payload` 决定，可以先打开 `output/facts.json` 看一遍。
- **词频默认不发送。** 高频词和口头禅本身就是隐私，相关 facts 标记为 `sensitive`，只有在 profile 里设置 `privacy.send_vocabulary: true` 才会进入模型输入。
- **仓库里没有真实数据。** `.gitignore` 排除了 `data/`、`output/` 和除示例外的所有 profile。示例数据由 `examples/synthetic/generate.py` 随机生成，人物与内容均为虚构。
- **profile 里的内容会被发送。** 显示名、关系节点、行程中的城市和日期，以及 `context` 里的背景（可用 `privacy.send_context: false` 关闭）会进入模型输入。不想发送的信息不要写进 profile。
- **图件和表格留在本机。** 词云、口头禅等图件会显示真实的词，`output/tables/` 里有词频表；分享前请自己过目。
- 报告生成后是否分享、分享给谁，由你们自己决定。

## 快速开始

```bash
pip install -e ".[story,zh]"
```

```bash
python examples/synthetic/generate.py examples/synthetic/messages.csv
```

```bash
couplechat analyze examples/synthetic/messages.csv
```

```bash
couplechat story --offline
```

```bash
couplechat render
```

`--offline` 使用固定模板，不调用模型，适合先确认流程能跑通。

### 调用大模型

需要 Anthropic API 凭据（环境变量 `ANTHROPIC_API_KEY`）。默认模型为 `claude-opus-5-5`，可在 profile 的 `story.model` 中修改。请求启用了服务端回退：如果模型拒绝某次请求，API 会自动在备用模型上重试。

```bash
couplechat story
```

列出候选故事线后，挑一条并写正文，同时审稿：

```bash
couplechat story --pick 1 --review
```

对稿子有意见时，把意见传回去重写：

```bash
couplechat story --pick 1 --feedback "第二章太长，压缩一半"
```

```bash
couplechat render --strict
```

### 用自己的数据

1. 复制 `profiles/example.yaml` 为 `profiles/<名字>.yaml`，改成你们的情况。
2. 把导出文件放进 `data/`。通用 CSV 格式只需要四列：`timestamp, sender, kind, text`。其他格式见 `src/couplechat/ingest/`。
3. 运行时带上 `--profile` 和 `--out`：

```bash
couplechat --profile profiles/<名字>.yaml --out output/<名字> analyze data/<导出文件> --format csv
```

## 扩展

- **新的导出格式**：在 `ingest/` 里写一个返回 `ts, sender, kind, text` 四列的函数，并登记到 `ADAPTERS`。
- **新的功能组**：在 `analyses/` 里新建一个文件，写 `run(ctx)`：开头用 `ctx.facts.module(name, applied, reason)` 说明是否适用，再用 `ctx.facts.add(...)` 添加数字，并把它加进 `analyses/__init__.py` 的 `ANALYSES`。
- **新的图**：在所属功能组里画好后调用 `ctx.figure(fig, 编号, 标题, 组名, shows)`。其中的 `shows` 是给模型看的一句话说明。
- **新的词表或问候规则**：改 `lexicons/` 下的文件，或在 profile 的 `lexicons` 里追加。
- **新的文风或语言**：改 profile 里的 `story.tone` 和 `story.language`，或直接改 `prompts/` 下的提示词。

## 测试

```bash
pip install -e ".[dev]"
```

```bash
pytest
```

测试只使用合成数据，不联网。

## 已知限制

- 目前输出 Markdown；LaTeX 或 HTML 排版尚未实现。
- 没有安装 `jieba` 时，中文词频退化为相邻两字切分，语言组的图会很粗糙，建议安装。
- 非整点时差（如 5.5 小时）在双时钟图中按四舍五入对齐。
- `wechat-json` 适配器是模板，字段名需要按你使用的导出工具调整。
- 通话事件通常只有时间戳，没有时长和接通状态。

## 许可

MIT
