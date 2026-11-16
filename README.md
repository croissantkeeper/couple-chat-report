# couplechat

**English** | [中文](README.zh-CN.md)

Turn a two-person chat export into a report that is backed by data and written by a language model.

Every couple is different. Some live in different time zones and some in the same city; some travel a lot; some never call. This project separates three things: the couple's own situation, the general statistics, and the storytelling. Analysing a different couple only takes a different profile file.

The tool was built for Chinese-language WeChat chats, so the word lists, greeting rules, prompts and figure labels are in Chinese. The pipeline itself is language-neutral; see [Extending](#extending).

## Gallery

Every figure below is drawn from fictional data produced by `examples/synthetic/generate.py`. The two people, 阿橘 (A) and 小鲸 (B), do not exist. All 27 figures are listed in [docs/figures.md](docs/figures.md).

**Relationship timeline**: daily chat volume against the relationship milestones, and how often affectionate words appear in each phase.

![Relationship timeline](docs/images/phase_timeline.png)

**Two clocks**: both people's chat hours aligned to the same instant, showing when in each person's day they meet.

![Two clocks, one chat window](docs/images/two_clocks.png)

**How the chat window settled**: the share of each week's text by hour; dashed lines mark a change in the time difference.

![Chat hours week by week](docs/images/weekly_hours.png)

**Who speaks first**: each person's share of conversation starts per phase, and the hour they usually start at.

![Who starts a conversation, and when](docs/images/session_starts.png)

**Itinerary and chat volume**: the background colour is the city someone was in, showing whether chat volume moves with location.

![Itinerary and chat volume](docs/images/itinerary.png)

**Chat calendar**

![Chat calendar](docs/images/calendar.png)

## Design

```
export ──ingest──▶ canonical message table ──analyses (nine groups)──▶ facts.json + figures + tables
                                                                    │
profile.yaml (names, itinerary, milestones, context, tone) ─────────┤
                                                                    ▼
                                   story: propose storylines ▶ write ▶ review
                                                                    ▼
                                   render: fill in numbers, check ▶ report.md
```

- **profile** (`profiles/*.yaml`): everything that differs between couples. Display names, each person's itinerary and time zones, relationship milestones, extra word lists, background supplied by the couple, and the tone of the report.
- **ingest** (`src/couplechat/ingest/`): one adapter per export format, each producing the same message table. Everything downstream reads only that table.
- **analyses** (`src/couplechat/analyses/`): nine groups by function. Each group owns its numbers, figures and tables; it computes and does not interpret. Each group first decides whether it applies to this couple, so a same-city couple gets "timezones: not applied" instead of an error.
- **facts.json**: every number the report may cite, each with an id and a definition. See [docs/facts-schema.md](docs/facts-schema.md).
- **story** (`src/couplechat/story/`, prompts in `prompts/`): three model calls. The first proposes two or three storylines for you to choose from, the second writes the report for the chosen one, and the third reviews it.
- **render** (`src/couplechat/render/`): replaces placeholders with numbers and checks the draft for numbers typed by hand.

### The model never writes numbers

When the model writes the report it does not type numbers. It writes placeholders such as `{{volume.text.A}}`, and the renderer fills them in. Numbers therefore cannot be invented, and the text does not need rewriting when the statistics are rerun. `render` flags unknown ids and hand-typed multi-digit numbers.

## Nine analysis groups, 27 figures

| Group | Question it answers | Figures | Applies when |
|---|---|---|---|
| `volume` | How much was said, by whom, in which media | daily trend, monthly distribution, weekly share, calendar, message types, length and daily balance | always |
| `rhythm` | When in the day and week each person chats | weekday × hour, weekly hours, hourly spread, late night | always |
| `timezones` | When in each person's day the two meet | two clocks, before and after a clock change | the clocks differ on enough days |
| `sessions` | Who starts, how long, how fast the replies | session shape, session starts, reply rhythm, all gaps | always |
| `language` | Each person's catchphrases and the words they share | word clouds, shared words, distinctive words, catchphrases, word lists by week | always (sensitive content) |
| `greetings` | Whose clock a good night follows, and how it is answered | greeting clocks, greeting pairs and good-night direction | enough greetings are matched |
| `relationship` | What changed around the milestones, and how things are lately | phase timeline, recent comparison | the profile has milestones; enough days |
| `calls` | How much happens in calls and not in text | weekly call events | the export has call events |
| `itinerary` | Whether chat volume moves with where someone was | itinerary | the profile lists more than one location |

Figure ids and descriptions are in [docs/figures.md](docs/figures.md). Tables are written to `output/tables/`.

## Privacy

A chat history belongs to two people. Make sure both agree before using this.

- **Only aggregates are sent to the model by default.** Raw messages never leave your machine. What is sent is decided by `facts.llm_payload`; you can read `output/facts.json` first.
- **Word frequencies are not sent by default.** Frequent words and catchphrases are private in themselves. Those facts are flagged `sensitive` and reach the model only if the profile sets `privacy.send_vocabulary: true`.
- **The repository holds no real data.** `.gitignore` excludes `data/`, `output/` and every profile except the example. The example data is generated at random by `examples/synthetic/generate.py`; the people and the content are fictional.
- **What you write in the profile is sent.** Display names, milestones, the cities and dates of the itinerary, and the `context` lines (switch them off with `privacy.send_context: false`) go into the model input. Leave out anything you do not want sent.
- **Figures and tables stay on your machine.** Word clouds and catchphrase charts show real words, and `output/tables/` holds a vocabulary table. Look through them before sharing.
- Whether to share the finished report, and with whom, is up to the two of you.

## Quick start

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

`--offline` uses a fixed template and calls no model. Use it to confirm that the pipeline runs.

### Calling the model

You need Anthropic API credentials (the `ANTHROPIC_API_KEY` environment variable). The default model is `claude-opus-5-5`; change it in the profile under `story.model`. Requests enable server-side fallback: if the model declines a request, the API retries it on a fallback model.

```bash
couplechat story
```

After the candidate storylines are listed, pick one, write the report and review it:

```bash
couplechat story --pick 1 --review
```

If you want changes, pass your comments back for a rewrite:

```bash
couplechat story --pick 1 --feedback "Chapter 2 is too long; cut it by half"
```

```bash
couplechat render --strict
```

### Using your own data

1. Copy `profiles/example.yaml` to `profiles/<name>.yaml` and edit it to match the two of you.
2. Put the export under `data/`. Supported formats are listed below.
3. Run with `--profile` and `--out`:

```bash
couplechat --profile profiles/<name>.yaml --out output/<name> analyze data/<export> --format csv
```

### Supported export formats

| `--format` | Source | Notes |
|---|---|---|
| `moect` | WeChat history exported with [Moect](https://github.com/mofan6/Moect) | Pass the export folder. Senders are reported as `self` (the exporting account) and `other`; assign them to the two people under `source_names` in the profile |
| `csv` | Generic CSV | Four columns: `timestamp, sender, kind, text`. The easiest target to convert other tools' output into |
| `wechat-json` | JSON from other tools | A template; adjust the field names to your tool |

Example with a Moect export:

```bash
couplechat --profile profiles/<name>.yaml --out output/<name> analyze data/<moect-export-folder> --format moect
```

This project only reads files you have exported yourself. It does not export chat histories and is not responsible for that step; follow the export tool's own instructions and licence.

## Extending

- **A new export format**: write a function in `ingest/` that returns the four columns `ts, sender, kind, text`, and register it in `ADAPTERS`.
- **A new analysis group**: add a file under `analyses/` with `run(ctx)`. Start by calling `ctx.facts.module(name, applied, reason)` to say whether it applies, add numbers with `ctx.facts.add(...)`, and append the module to `ANALYSES` in `analyses/__init__.py`.
- **A new figure**: draw it inside its group and call `ctx.figure(fig, id, title, group, shows)`. `shows` is the one-sentence description the model reads.
- **New word lists or greeting rules**: edit the files under `lexicons/`, or add to `lexicons` in the profile.
- **Another tone or language**: change `story.tone` and `story.language` in the profile, or edit the prompts under `prompts/`. For a non-Chinese chat you will also want to replace the word lists, the greeting rules and the stop words under `lexicons/`.

## Tests

```bash
pip install -e ".[dev]"
```

```bash
pytest
```

The tests use synthetic data only and make no network calls.

## Known limitations

- Figure labels, word lists, greeting rules and prompts are in Chinese.
- Output is Markdown; LaTeX or HTML layout is not implemented yet.
- Without `jieba`, Chinese word counts fall back to overlapping two-character pieces and the language figures become rough. Installing it is recommended.
- A time difference that is not a whole number of hours (5.5, for example) is rounded when the two clocks are aligned.
- The `moect` adapter follows the file structure Moect produces today and may need updating if that tool changes its format. The `wechat-json` adapter is only a template.
- Call events usually carry only a timestamp, with no duration and no connection status.

## Licence

MIT
