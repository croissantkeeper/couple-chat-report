# facts.json 格式

[English](facts-schema.md) | **中文**

`facts.json` 是统计层与叙述层之间唯一的接口。叙述层（大模型和模板）只能引用这里的数字。

```json
{
  "meta": {
    "first_day": "2025-03-01",
    "last_day": "2025-05-31",
    "labels": {"A": "阿橘", "B": "小鲸"},
    "session_gap_minutes": 60,
    "phases": [{"key": "met", "label": "认识", "first": "2025-03-01", "last": "2025-03-20"}],
    "itinerary": [{"person": "A", "segment": 1, "city": "上海", "first": "2025-03-01", "last": "2025-03-20"}]
  },
  "modules": {
    "timezones": {"applied": true, "reason": "两人时钟不同的天数为 72"},
    "calls": {"applied": false, "reason": "导出中没有通话事件"}
  },
  "figures": [
    {"id": "daily_trend", "path": "figures/daily_trend.png", "title": "每日文字量与7日均线",
     "module": "volume", "shows": "每天两人各发多少条文字……"}
  ],
  "facts": {
    "volume.text.A": {"value": 2100, "unit": "", "desc": "阿橘的文字消息条数",
                      "module": "volume", "sensitive": false}
  }
}
```

## 字段

- **meta**：窗口起止、显示名、会话阈值，以及阶段和行程的划分结果。
- **modules**：每个可选模块是否启用及原因。`reason` 同时用来写明口径限制，模型会读到它。
- **figures**：图件目录。`shows` 用一句话说明这张图能看出什么，供模型选图。
- **facts**：键为编号，值包含：
  - `value`：整数、小数、字符串（如日期）。
  - `unit`：`%` 表示数值已是百分数，渲染时自动加百分号；其他单位只作说明。
  - `desc`：口径说明，写清统计的是什么、不是什么。
  - `module`：来自哪个模块。
  - `sensitive`：为 `true` 时默认不发送给模型（目前是词频类）。

## 编号约定

- 用点分层：`领域.指标.人`，例如 `sessions.start_share.A`。
- 涉及某个人时以 `.A` 或 `.B` 结尾；显示名在 `meta.labels`。
- 阶段类用 profile 里节点的 `key`：`phase.together.daily_median`。
- 行程类用人和段号：`itinerary.B.seg2.daily_median`。
- 编号一旦发布尽量不改，正文里的占位符依赖它。

## 在正文中引用

- 数字：`{{volume.text.A}}`
- 图件：单独一行的 `[[figure:daily_trend]]`

渲染规则：整数加千分位，小数保留一位，`unit` 为 `%` 的加百分号。
