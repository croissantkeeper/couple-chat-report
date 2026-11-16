"""Narrative layer: propose storylines, write chapters with placeholders, review claims.

Only facts.json aggregates are sent to the model (see facts.llm_payload); raw
messages never leave the machine. Every stage writes its result to
<output>/story/ so reruns of the statistics do not re-call the model.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..facts import llm_payload
from ..profile import ROOT, Profile

PROMPTS = ROOT / "prompts"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
CATALOGUE_MARK = "<!--figure-catalogue-->"   # generated captions follow; the hand-typed-number check stops here
GROUP_TITLES = {"volume": "聊天量与对称性", "rhythm": "作息节奏", "timezones": "两套时钟", "sessions": "会话与回应", "language": "语言",
                "greetings": "问候", "relationship": "关系阶段", "calls": "通话", "itinerary": "行程"}


def _ask(profile: Profile, system: str, user: str) -> str:
    import anthropic  # imported lazily so the statistics work without the SDK

    client = anthropic.Anthropic()
    with client.beta.messages.stream(
        model=profile.story["model"],
        max_tokens=32000,
        thinking={"type": "adaptive"},
        betas=[FALLBACK_BETA],
        fallbacks="default",        # if the model declines, the API retries on a fallback model
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        message = stream.get_final_message()
    if message.stop_reason == "refusal":
        raise RuntimeError("模型拒绝了这次请求；请检查 context 与词表中是否有不适合发送的内容。")
    if message.stop_reason == "max_tokens":
        raise RuntimeError("输出被截断；请减少章节数或分章生成。")
    return "".join(block.text for block in message.content if block.type == "text")


def _json(text: str):
    match = re.search(r"```json\s*(.*?)```", text, re.S)
    return json.loads(match.group(1) if match else text)


def _material(profile: Profile, data: dict) -> str:
    payload = llm_payload(data, profile.privacy["send_vocabulary"])
    context = profile.context if profile.privacy["send_context"] else []
    return json.dumps({"tone": profile.story["tone"], "language": profile.story["language"],
                       "context_from_the_couple": context, "data": payload}, ensure_ascii=False, indent=1)


def propose(profile: Profile, data: dict, out: Path) -> list[dict]:
    """Stage 1: two or three candidate storylines; the user picks one."""
    reply = _ask(profile, (PROMPTS / "storyline.md").read_text(encoding="utf-8"), _material(profile, data))
    storylines = _json(reply)
    (out / "storylines.json").write_text(json.dumps(storylines, ensure_ascii=False, indent=2), encoding="utf-8")
    return storylines


def write(profile: Profile, data: dict, storyline: dict, out: Path, feedback: str = "") -> str:
    """Stage 2: full draft in Markdown; numbers appear only as {{fact.id}} placeholders."""
    user = _material(profile, data) + "\n\n# 选定的故事线\n" + json.dumps(storyline, ensure_ascii=False, indent=1)
    if feedback:
        user += "\n\n# 用户对上一稿的意见\n" + feedback
    draft = _ask(profile, (PROMPTS / "section.md").read_text(encoding="utf-8"), user)
    (out / "draft.md").write_text(draft, encoding="utf-8")
    return draft


def review(profile: Profile, data: dict, draft: str, out: Path) -> list[dict]:
    """Stage 3: a second pass that flags sentences the data does not support."""
    user = _material(profile, data) + "\n\n# 待审稿件\n" + draft
    findings = _json(_ask(profile, (PROMPTS / "review.md").read_text(encoding="utf-8"), user))
    (out / "review.json").write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
    return findings


def offline_draft(data: dict) -> str:
    """No-API fallback: a plain template so the pipeline runs end to end without a model."""
    text = (PROMPTS / "offline_draft.md").read_text(encoding="utf-8")
    applied = {name for name, m in data["modules"].items() if m["applied"]}
    figures = {f["id"] for f in data["figures"]}

    def keep(match: re.Match) -> str:
        need = match.group(1)
        return match.group(2) if need in applied or need in figures else ""

    text = re.sub(r"<!--if:(\w+)-->(.*?)<!--end-->", keep, text, flags=re.S)
    labels = data["meta"]["labels"]
    text = text.replace("【A】", labels["A"]).replace("【B】", labels["B"])
    # Then every figure, group by group, each with the sentence that says what it shows.
    used = set(re.findall(r"\[\[figure:(\w+)\]\]", text))
    parts = [text.rstrip(), "", CATALOGUE_MARK, "", "## 全部图件", "", "下面按功能组列出本次生成的全部图件，每张图下方说明它能看出什么。"]
    for group, title in GROUP_TITLES.items():
        figures = [f for f in data["figures"] if f["module"] == group and f["id"] not in used]
        if not figures:
            continue
        parts += ["", f"### {title}"]
        reason = data["modules"].get(group, {}).get("reason")
        if reason:
            parts += ["", f"> 口径：{reason}"]
        for f in figures:
            parts += ["", f"**{f['title']}**　{f['shows']}", "", f"[[figure:{f['id']}]]"]
    return chr(10).join(parts) + chr(10)
