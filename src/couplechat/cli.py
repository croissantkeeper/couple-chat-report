"""Command line.

  couplechat demo                      try it on fictional data, no setup needed
  couplechat init EXPORT --format F    look at your export and write a starter profile
  couplechat run EXPORT --format F     analyze + report in one go (no model needed)

Step by step, when you want the model to write the report:
  couplechat analyze EXPORT            statistics, figures and facts.json
  couplechat story [--pick N]          propose storylines, then write the chosen one
  couplechat render                    fill in the numbers -> report.md and report.html
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from . import story
from .analyses import run_all
from .facts import Facts, load_facts
from .ingest import ADAPTERS, ingest
from .prepare import Context, prepare
from .profile import ROOT, load_profile
from .render import check_draft, render_html, render_markdown


def _analyze(profile_path: str, source: str, fmt: str, out: Path) -> None:
    profile = load_profile(profile_path)
    out.mkdir(parents=True, exist_ok=True)
    df = prepare(ingest(source, fmt, profile), profile)
    if df.empty:
        sys.exit("没有可用的消息：请检查 profile 里的 source_names 是否与导出中的发送者一致（可先运行 couplechat init 查看）。")
    for key in ("A", "B"):
        if not (df["sender"] == key).any():
            sys.exit(f"没有找到 {profile.label(key)} 的消息：请检查 profile 里 {key} 的 source_names。")
    facts = Facts()
    run_all(Context(df, profile, facts, out))
    facts.save(out / "facts.json")
    applied = [n for n, m in facts.modules.items() if m["applied"]]
    skipped = [n for n, m in facts.modules.items() if not m["applied"]]
    print(f"{len(df)} 条消息 -> {len(facts.facts)} 个 facts，{len(facts.figures)} 张图")
    print("启用的模块：", "、".join(applied) or "无")
    if skipped:
        print("跳过的模块：", "；".join(f"{n}（{facts.modules[n]['reason']}）" for n in skipped))


def _render(out: Path, strict: bool = False) -> None:
    data = load_facts(out / "facts.json")
    draft = (out / "story" / "draft.md").read_text(encoding="utf-8")
    problems = check_draft(draft, data)
    for p in problems:
        print("检查：", p)
    if problems and strict:
        sys.exit(f"{len(problems)} 处问题未解决，未生成报告。")
    markdown = render_markdown(draft, data)
    (out / "report.md").write_text(markdown, encoding="utf-8")
    (out / "report.html").write_text(render_html(markdown), encoding="utf-8")
    print("报告已生成：", (out / "report.html").resolve())


def _offline(out: Path) -> None:
    sdir = out / "story"
    sdir.mkdir(exist_ok=True)
    (sdir / "draft.md").write_text(story.offline_draft(load_facts(out / "facts.json")), encoding="utf-8")


def cmd_analyze(args) -> None:
    _analyze(args.profile, args.input, args.format, Path(args.out))


def cmd_story(args) -> None:
    profile = load_profile(args.profile)
    out = Path(args.out)
    data = load_facts(out / "facts.json")
    sdir = out / "story"
    sdir.mkdir(exist_ok=True)
    if args.offline:
        _offline(out)
        print("已用固定模板生成 story/draft.md（未调用大模型）")
        return
    if args.pick is None:
        for i, s in enumerate(story.propose(profile, data, sdir), 1):
            print(f"[{i}] {s['title']}\n    {s['thesis']}")
        print("挑一条后运行：couplechat story --pick N")
        return
    storylines = json.loads((sdir / "storylines.json").read_text(encoding="utf-8"))
    draft = story.write(profile, data, storylines[args.pick - 1], sdir, feedback=args.feedback or "")
    print("已写入 story/draft.md")
    if args.review:
        findings = story.review(profile, data, draft, sdir)
        print(f"审稿发现 {len(findings)} 处问题，见 story/review.json")


def cmd_render(args) -> None:
    _render(Path(args.out), args.strict)


def cmd_run(args) -> None:
    out = Path(args.out)
    _analyze(args.profile, args.input, args.format, out)
    _offline(out)
    _render(out)
    print("这是不调用大模型的图表版报告。想让模型来写故事：couplechat story，然后 couplechat story --pick N，最后 couplechat render。")


def cmd_demo(args) -> None:
    out = Path(args.out if args.out != "output" else "demo")
    out.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("generate", ROOT / "examples" / "synthetic" / "generate.py")
    generate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generate)
    generate.main(str(out / "messages.csv"))
    _analyze(str(ROOT / "profiles" / "example.yaml"), str(out / "messages.csv"), "csv", out)
    _offline(out)
    _render(out)


def cmd_init(args) -> None:
    raw = ADAPTERS[args.format](Path(args.input))
    counts = raw["sender"].astype(str).value_counts()
    print("导出里的发送者：")
    for name, n in counts.items():
        print(f"  {name}: {n} 条")
    if len(counts) < 2:
        sys.exit("只找到一个发送者，无法分析两个人的聊天。")
    if len(counts) > 2:
        print("发送者多于两个：下面取消息最多的两个，其余会被忽略。")
    first, second = list(counts.index[:2])
    import pandas as pd
    ts = pd.to_datetime(raw["ts"], utc=True, format="ISO8601") if not pd.api.types.is_datetime64_any_dtype(raw["ts"]) else raw["ts"]
    print(f"时间范围：{ts.min():%Y-%m-%d} 至 {ts.max():%Y-%m-%d}（UTC）")
    target = Path(args.write or f"profiles/{args.name}.yaml")
    if target.exists() and not args.force:
        sys.exit(f"{target} 已存在；换一个 --name，或加 --force 覆盖。")
    template = (ROOT / "profiles" / "starter.yaml").read_text(encoding="utf-8")
    text = (template.replace("__SENDER_A__", json.dumps(first, ensure_ascii=False)).replace("__SENDER_B__", json.dumps(second, ensure_ascii=False))
            .replace("__TZ_A__", args.tz_a).replace("__TZ_B__", args.tz_b).replace("__TZ_REF__", args.tz_b))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"已写入 {target}。请打开它，改成你们的称呼、时区和关系节点，然后运行：")
    print(f"  couplechat --profile {target.as_posix()} --out output/{args.name} run {args.input} --format {args.format}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="couplechat", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", default="profiles/example.yaml")
    parser.add_argument("--out", default="output")
    sub = parser.add_subparsers(dest="command", required=True)
    formats = sorted(ADAPTERS)

    d = sub.add_parser("demo", help="用虚构数据跑一遍，生成 demo/report.html")
    d.set_defaults(func=cmd_demo)
    i = sub.add_parser("init", help="查看导出里的发送者，并生成一份起步用的 profile")
    i.add_argument("input")
    i.add_argument("--format", default="csv", choices=formats)
    i.add_argument("--name", default="mine", help="profile 的名字，写入 profiles/<name>.yaml")
    i.add_argument("--write", help="直接指定写入路径")
    i.add_argument("--tz-a", default="Asia/Shanghai", help="第一个人的默认时区")
    i.add_argument("--tz-b", default="Asia/Shanghai", help="第二个人的默认时区")
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_init)
    r = sub.add_parser("run", help="一步完成：统计、图件、图表版报告（不调用模型）")
    r.add_argument("input")
    r.add_argument("--format", default="csv", choices=formats)
    r.set_defaults(func=cmd_run)
    a = sub.add_parser("analyze", help="读取导出，计算 facts.json 和图件")
    a.add_argument("input")
    a.add_argument("--format", default="csv", choices=formats)
    a.set_defaults(func=cmd_analyze)
    s = sub.add_parser("story", help="调用大模型：提出故事线，或按选定故事线写正文")
    s.add_argument("--pick", type=int, help="选定第几条故事线并写正文")
    s.add_argument("--feedback", help="对上一稿的修改意见")
    s.add_argument("--review", action="store_true", help="写完后再调用一次模型审稿")
    s.add_argument("--offline", action="store_true", help="不调用模型，用固定模板")
    s.set_defaults(func=cmd_story)
    e = sub.add_parser("render", help="填入数字并生成 report.md 和 report.html")
    e.add_argument("--strict", action="store_true", help="检查不通过时不生成")
    e.set_defaults(func=cmd_render)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
