import ast
import io
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = sorted((ROOT / "backend/src").rglob("*.py"))
FRONTEND = sorted(
    p
    for p in (ROOT / "frontend/src").rglob("*")
    if p.suffix in {".ts", ".vue"} and not p.name.endswith(".test.ts")
)
PLAIN = re.compile(r"[A-Za-z0-9 .,\n]+")


def test_docstrings_are_plain_text_on_functions_only() -> None:
    for path in SOURCES:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(
                node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
            ):
                continue
            doc = ast.get_docstring(node, clean=True)
            if doc is None:
                continue
            assert not isinstance(node, ast.Module | ast.ClassDef), f"{path}: {doc[:40]}"
            assert PLAIN.fullmatch(doc), f"{path}:{node.lineno} {doc!r}"


def test_only_todo_and_tool_comments_in_python() -> None:
    allowed = re.compile(r"# (TODO\b.*|noqa: [A-Z0-9, ]+)")
    for path in SOURCES:
        tokens = tokenize.generate_tokens(io.StringIO(path.read_text()).readline)
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                assert allowed.fullmatch(tok.string), f"{path}:{tok.start[0]} {tok.string}"


def test_jsdoc_is_plain_text() -> None:
    for path in FRONTEND:
        for block in re.findall(r"/\*\*([\s\S]*?)\*/", path.read_text()):
            text = re.sub(r"^\s*\* ?", "", block, flags=re.M).strip()
            assert PLAIN.fullmatch(text), f"{path}: {text[:40]}"
