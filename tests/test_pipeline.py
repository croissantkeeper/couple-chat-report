"""End-to-end test on synthetic data: no real chat data, no network."""
import importlib.util
import json
from pathlib import Path

from couplechat.cli import main
from couplechat.facts import llm_payload, load_facts
from couplechat.render import check_draft

ROOT = Path(__file__).resolve().parents[1]


def _generate(path: Path) -> None:
    spec = importlib.util.spec_from_file_location("generate", ROOT / "examples" / "synthetic" / "generate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main(str(path))


def _run(tmp_path: Path, profile: Path) -> dict:
    csv = tmp_path / "messages.csv"
    _generate(csv)
    out = tmp_path / "out"
    base = ["--profile", str(profile), "--out", str(out)]
    main(base + ["analyze", str(csv)])
    main(base + ["story", "--offline"])
    main(base + ["render", "--strict"])
    assert "{{" not in (out / "report.md").read_text(encoding="utf-8")
    return load_facts(out / "facts.json")


def test_long_distance_couple(tmp_path):
    data = _run(tmp_path, ROOT / "profiles" / "example.yaml")
    assert data["modules"]["timezones"]["applied"]
    assert data["modules"]["itinerary"]["applied"]
    assert data["modules"]["calls"]["applied"]
    assert len(data["figures"]) == 27
    facts = data["facts"]
    assert facts["volume.text.A"]["value"] + facts["volume.text.B"]["value"] == facts["volume.text"]["value"]
    # the synthetic A mostly answers B's good night from A's own afternoon
    assert facts["tz.sleep_wish.in_receiver_night.A"]["value"] > facts["tz.sleep_wish.in_sender_night.A"]["value"]
    # the offline report shows every figure, each exactly once
    html = (tmp_path / "out" / "report.html").read_text(encoding="utf-8")
    assert html.count("<img") == 27


def test_same_city_couple_skips_modules(tmp_path):
    text = (ROOT / "profiles" / "example.yaml").read_text(encoding="utf-8")
    text = text.replace("Europe/Berlin", "Asia/Shanghai")
    profile = tmp_path / "same_city.yaml"
    profile.write_text(text, encoding="utf-8")
    data = _run(tmp_path, profile)
    assert not data["modules"]["timezones"]["applied"]
    assert not any(k.startswith("tz.") for k in data["facts"])
    assert {f["id"] for f in data["figures"]}.isdisjoint({"two_clocks", "clock_change"})


def test_vocabulary_is_not_sent_by_default(tmp_path):
    data = _run(tmp_path, ROOT / "profiles" / "example.yaml")
    payload = json.dumps(llm_payload(data, send_vocabulary=False), ensure_ascii=False)
    assert "vocab." not in payload
    assert "vocab." in json.dumps(llm_payload(data, send_vocabulary=True), ensure_ascii=False)


def test_moect_adapter(tmp_path):
    from couplechat.ingest import ingest
    from couplechat.profile import load_profile

    messages = [
        {"create_time": 1741000000, "is_sender": True, "kind": "text", "text": "你好", "server_id": "1", "session": "s"},
        {"create_time": 1741000060, "is_sender": False, "kind": "emoji", "text": "", "server_id": "2", "session": "s"},
        {"create_time": 1741000060, "is_sender": False, "kind": "emoji", "text": "", "server_id": "2", "session": "s"},
        {"create_time": 1741000120, "is_sender": False, "kind": "voip", "text": "", "server_id": "3", "session": "s"},
        {"create_time": 1741000180, "is_sender": True, "kind": "text", "text": "你撤回了一条消息", "server_id": "4", "session": "s"},
    ]
    folder = tmp_path / "export" / "chat"
    folder.mkdir(parents=True)
    (folder / "c000001.js").write_text("window.__wxChunk=" + json.dumps(messages, ensure_ascii=False) + ";", encoding="utf-8")
    text = (ROOT / "profiles" / "example.yaml").read_text(encoding="utf-8")
    profile = tmp_path / "moect.yaml"
    profile.write_text(text.replace("source_names: [A, 阿橘]", "source_names: [self]").replace("source_names: [B, 小鲸]", "source_names: [other]"), encoding="utf-8")
    df = ingest(tmp_path / "export", "moect", load_profile(profile))
    assert list(df["sender"]) == ["A", "B", "B"]          # duplicate and system notice dropped
    assert list(df["kind"]) == ["text", "sticker", "call"]


def test_init_writes_a_profile_that_runs(tmp_path):
    csv = tmp_path / "messages.csv"
    _generate(csv)
    profile = tmp_path / "mine.yaml"
    main(["init", str(csv), "--format", "csv", "--write", str(profile)])
    out = tmp_path / "out"
    main(["--profile", str(profile), "--out", str(out), "run", str(csv)])
    data = load_facts(out / "facts.json")
    assert data["modules"]["volume"]["applied"]
    assert not data["modules"]["timezones"]["applied"]      # the starter profile puts both people on one clock
    assert (out / "report.html").exists()


def test_handwritten_numbers_are_flagged():
    data = {"facts": {"volume.text": {"value": 10, "unit": "", "desc": ""}}, "figures": []}
    assert check_draft("共 {{volume.text}} 条。", data) == []
    assert check_draft("共 1234 条。", data)
    assert check_draft("共 {{no.such.fact}} 条。", data)
