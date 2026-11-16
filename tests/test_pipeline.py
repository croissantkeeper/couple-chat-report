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
    # the synthetic B says good night at B's own bedtime; A answers from the afternoon
    assert facts["tz.sleep_wish.in_receiver_night.A"]["value"] > 90
    assert facts["tz.sleep_wish.in_sender_night.A"]["value"] < 10


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


def test_handwritten_numbers_are_flagged():
    data = {"facts": {"volume.text": {"value": 10, "unit": "", "desc": ""}}, "figures": []}
    assert check_draft("共 {{volume.text}} 条。", data) == []
    assert check_draft("共 1234 条。", data)
    assert check_draft("共 {{no.such.fact}} 条。", data)
