# facts.json format

**English** | [中文](facts-schema.zh-CN.md)

`facts.json` is the only interface between the statistics and the narrative. The narrative layer (the model and the templates) may cite numbers only from here.

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

Descriptions (`desc`, `reason`, `shows`, `title`) are generated in Chinese.

## Fields

- **meta**: the first and last day, display names, the session threshold, and the resulting phases and itinerary segments.
- **modules**: whether each analysis group was applied, and why. `reason` also states the limits of what the numbers mean, and the model reads it.
- **figures**: the figure catalogue. `shows` says in one sentence what the figure reveals, so the model can choose figures.
- **facts**: keyed by id. Each value has:
  - `value`: an integer, a decimal, or a string such as a date.
  - `unit`: `%` means the value is already a percentage and the renderer appends the sign; other units are informational.
  - `desc`: the definition, saying what is counted and what is not.
  - `module`: the group it came from.
  - `sensitive`: when `true`, the fact is not sent to the model by default (currently the vocabulary facts).

## Id conventions

- Dot-separated levels: `area.metric.person`, for example `sessions.start_share.A`.
- Ids about one person end in `.A` or `.B`; display names are in `meta.labels`.
- Phase facts use the milestone `key` from the profile: `phase.together.daily_median`.
- Itinerary facts use the person and segment number: `itinerary.B.seg2.daily_median`.
- Ids contain only letters, digits, underscores and dots.
- Avoid renaming an id once published; placeholders in drafts depend on it.

## Citing in a draft

- A number: `{{volume.text.A}}`
- A figure, on a line of its own: `[[figure:daily_trend]]`

Rendering: integers get thousands separators, decimals keep one place, and values whose `unit` is `%` get a percent sign.
