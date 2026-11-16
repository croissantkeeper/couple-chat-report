# 【A】与【B】的聊天记录报告

这是不调用大模型时使用的固定模板，只陈述数字，不做解读。

## 概览

观察窗口为 {{days.calendar}} 天，其中 {{days.with_text}} 天有文字消息。全部记录 {{volume.records}} 条，文字消息 {{volume.text}} 条，典型的一天有 {{daily.median}} 条文字。

[[figure:daily_trend]]

## 两个人各说了多少

【A】发出 {{volume.text.A}} 条文字、{{volume.chars.A}} 个字符，单条长度中位数为 {{length.median.A}}；【B】发出 {{volume.text.B}} 条文字、{{volume.chars.B}} 个字符，单条长度中位数为 {{length.median.B}}。两人的字符数相差 {{volume.chars.diff}}，占总量的 {{volume.chars.diff_share}}。

会话由【A】开启的比例为 {{sessions.start_share.A}}，由【B】开启的比例为 {{sessions.start_share.B}}。进入对话后，【A】与【B】接话间隔的中位数分别为 {{reply.median_sec.A}} 秒和 {{reply.median_sec.B}} 秒。
<!--if:timezones-->

## 两套时钟

两人有 {{tz.days_apart}} 天处于不同时区，最常见的时差为 {{tz.offset_hours.mode}} 小时。异地期间，【A】发文字最多的当地小时是 {{tz.peak_local_hour.A}} 点，【B】是 {{tz.peak_local_hour.B}} 点。
<!--end-->
<!--if:two_clocks-->

[[figure:two_clocks]]
<!--end-->
<!--if:calls-->

## 通话

导出中共有 {{calls.events}} 条通话事件，分布在 {{calls.days}} 天。通话事件只有时间戳，不代表已接通，也没有时长。
<!--end-->
