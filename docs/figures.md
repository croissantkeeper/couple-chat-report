# Figure index

**English** | [中文](figures.zh-CN.md)

Figure ids are what the draft cites as `[[figure:id]]`. In `facts.json`, each figure also carries a one-sentence `shows` description that the model reads when choosing figures. Labels inside the figures are currently in Chinese.

## volume: how much, by whom, in which media

| Id | Shows |
|---|---|
| `daily_trend` | Daily text volume with a centred 7-day mean; vertical lines mark milestones |
| `monthly_distribution` | Median, interquartile range and mean of daily text volume for each month |
| `weekly_share` | Each person's weekly share of text messages and of all records |
| `calendar` | Daily text volume laid out as a calendar |
| `message_types` | Shares of text, quoted replies, stickers, images and so on |
| `length_and_balance` | Cumulative distribution of message length; scatter of the two people's daily characters |

## rhythm: each person's own clock

| Id | Shows |
|---|---|
| `weekday_hour` | Activity by weekday and local hour |
| `weekly_hours` | Share of each week's text by hour; dashed lines mark a change in the time difference |
| `hourly_spread` | Mean, median and interquartile range for each hour |
| `late_night` | Share of text sent late at night and share of days with late-night text, per clock-gap stage |

## timezones: the two clocks side by side

| Id | Shows |
|---|---|
| `two_clocks` | One panel per clock-gap stage, with both curves aligned to the same instant |
| `clock_change` | The 14 days before and after the latest change in the time difference, on both clocks |

## sessions: conversations and replies

| Id | Shows |
|---|---|
| `session_shape` | Cumulative distributions of span, record count and speaker switches for two-person sessions |
| `session_starts` | Who starts in each stage; the local hour at which each person starts |
| `reply_rhythm` | Reply gaps inside a session, split by whether the replier was in the small hours |
| `all_gaps` | All speaker-switch gaps, including those between sessions |

## language: words (sensitive content)

| Id | Shows |
|---|---|
| `word_clouds` | A word cloud for each person |
| `shared_words` | The most frequent words overall, mirrored for the two people |
| `distinctive_words` | Words each person uses most in excess of the other, per thousand words |
| `catchphrases` | Ranking of short phrases sent as a whole message |
| `lexicon_weekly` | Weekly rate of each word-list category |

## greetings

| Id | Shows |
|---|---|
| `greeting_clocks` | Hourly distribution of four greeting types on the sender's and the receiver's clock |
| `greeting_pairs` | Which greeting types answer which; whose night a sleep wish lands in |

## relationship: phases

| Id | Shows |
|---|---|
| `phase_timeline` | Daily text volume with milestones; affectionate-word rate per phase |
| `recent_comparison` | Text volume, session span and session count in the two most recent equal windows |

## calls

| Id | Shows |
|---|---|
| `calls_weekly` | Call-event records per week |

## itinerary

| Id | Shows |
|---|---|
| `itinerary` | Daily text and calls against a background of cities; typical daily volume per itinerary segment |
