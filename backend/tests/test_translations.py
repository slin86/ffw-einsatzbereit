import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_every_api_error_has_a_german_text() -> None:
    backend = "\n".join(p.read_text() for p in (ROOT / "backend/src").rglob("*.py"))
    details = set(re.findall(r'HTTP_\d+_[A-Z_]+,\s*"([^"]+)"', backend))
    assert len(details) > 20
    frontend = (ROOT / "frontend/src/api.ts").read_text()
    table = frontend[frontend.index("ERROR_TEXT") :]
    translated = set(re.findall(r'^\s*"([^"]+)":', table, flags=re.M))
    assert details - translated == set()
    assert translated - details == set()
