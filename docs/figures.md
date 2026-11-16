# 图件索引

图件编号用于正文中的 `[[figure:编号]]`。每张图在 `facts.json` 的 `figures` 里还带有一句 `shows` 说明，供模型选图。

## volume 聊天量与对称性

| 编号 | 内容 |
|---|---|
| `daily_trend` | 每日文字量与 7 日居中平均，竖线为关系节点 |
| `monthly_distribution` | 各月每日文字量的中位数、四分位区间和均值 |
| `weekly_share` | 每周两人在文字和全部记录中的占比 |
| `calendar` | 月历形式的每日文字量 |
| `message_types` | 文字、引用回复、表情包、图片等的占比 |
| `length_and_balance` | 单条长度的累计分布；每天两人字符数的散点 |

## rhythm 作息节奏

| 编号 | 内容 |
|---|---|
| `weekday_hour` | 星期 × 当地小时的发言强度 |
| `weekly_hours` | 每周文字在各小时的占比，虚线为时差变化 |
| `hourly_spread` | 各小时的均值、中位数和四分位区间 |
| `late_night` | 各时差阶段的深夜文字占比与深夜天数占比 |

## timezones 两套时钟

| 编号 | 内容 |
|---|---|
| `two_clocks` | 每个时差阶段一栏，两人的曲线对齐到同一时刻 |
| `clock_change` | 最近一次时差变化前后各 14 天，在两套时钟上的分布 |

## sessions 会话与回应

| 编号 | 内容 |
|---|---|
| `session_shape` | 双人会话的跨度、记录数、切换次数的累计分布 |
| `session_starts` | 各阶段谁先开口；发起会话的当地小时 |
| `reply_rhythm` | 会话内的接话间隔，按接话者是否处于深夜分栏 |
| `all_gaps` | 不按会话截断的全部说话人切换间隔 |

## language 语言（内容敏感）

| 编号 | 内容 |
|---|---|
| `word_clouds` | 两人各自的词云 |
| `shared_words` | 共同高频词的镜像对照 |
| `distinctive_words` | 每千词频率比对方高出最多的词 |
| `catchphrases` | 整条消息只有这一句的短句排行 |
| `lexicon_weekly` | 词表各类别的逐周出现率 |

## greetings 问候

| 编号 | 内容 |
|---|---|
| `greeting_clocks` | 四类问候在发送者时钟和接收者时钟下的小时分布 |
| `greeting_pairs` | 先后两句问候的类型配对；睡眠祝愿落在谁的夜间 |

## relationship 关系阶段

| 编号 | 内容 |
|---|---|
| `phase_timeline` | 每日文字量与关系节点；各阶段的亲昵词出现率 |
| `recent_comparison` | 最近两个等长窗口的文字量、会话跨度和会话数 |

## calls 通话

| 编号 | 内容 |
|---|---|
| `calls_weekly` | 每周通话事件记录数 |

## itinerary 行程

| 编号 | 内容 |
|---|---|
| `itinerary` | 所在城市背景下的每日文字与通话；各行程段的典型日文字量 |
