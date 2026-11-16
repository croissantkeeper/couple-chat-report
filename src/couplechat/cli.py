"""Command line: analyze -> story (propose / write / review) -> render."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .facts import Facts, load_facts
from .ingest import ADAPTERS, ingest
from .analyses import run_all
from .prepare import Context, prepare
from .profile import load_profile
from .render import check_draft, render_markdown
from . import story


def cmd_analyze(args) -> None:
    profile = load_profile(args.profile)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df = prepare(ingest(args.input, args.format, profile), profile)
    if df.empty:
        sys.exit("没有可用的消息：请检查 profile 里的 source_names 是否与导出中的发送者一致。")
    facts = Facts()
    run_all(Context(df, profile, facts, out))
    facts.save(out / "facts.json")
    applied = [n for n, m in facts.modules.items() if m["applied"]]
    skipped = [n for n, m in facts.modules.items() if not m["applied"]]
    print(f"{len(df)} 条消息 -> {len(facts.facts)} 个 facts，{len(facts.figures)} 张图")
    print("启用的模块：", "、".join(applied) or "无")
    if skipped:
        print("跳过的模块：", "；".join(f"{n}（{facts.modules[n]['reason']}）" for n in skipped))


def cmd_story(args) -> None:
    profile = load_profile(args.profile)
    out = Path(args.out)
    data = load_facts(out / "facts.json")
    sdir = out / "story"
    sdir.mkdir(exist_ok=True)
    if args.offline:
        (sdir / "draft.md").write_text(story.offline_draft(data), encoding="utf-8")
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
    out = Path(args.out)
    data = load_facts(out / "facts.json")
    draft = (out / "story" / "draft.md").read_text(encoding="utf-8")
    problems = check_draft(draft, data)
    for p in problems:
        print("检查：", p)
    if problems and args.strict:
        sys.exit(f"{len(problems)} 处问题未解决，未生成报告。")
    (out / "report.md").write_text(render_markdown(draft, data), encoding="utf-8")
    print("已生成", out / "report.md")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="couplechat", description=__doc__)
    parser.add_argument("--profile", default="profiles/example.yaml")
    parser.add_argument("--out", default="output")
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("analyze", help="读取导出，计算 facts.json 和图件")
    a.add_argument("input")
    a.add_argument("--format", default="csv", choices=sorted(ADAPTERS))
    a.set_defaults(func=cmd_analyze)
    s = sub.add_parser("story", help="调用大模型：提出故事线，或按选定故事线写正文")
    s.add_argument("--pick", type=int, help="选定第几条故事线并写正文")
    s.add_argument("--feedback", help="对上一稿的修改意见")
    s.add_argument("--review", action="store_true", help="写完后再调用一次模型审稿")
    s.add_argument("--offline", action="store_true", help="不调用模型，用固定模板")
    s.set_defaults(func=cmd_story)
    r = sub.add_parser("render", help="填入数字并生成 report.md")
    r.add_argument("--strict", action="store_true", help="检查不通过时不生成")
    r.set_defaults(func=cmd_render)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
