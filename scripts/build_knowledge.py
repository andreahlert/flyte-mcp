"""Scrape flyte-sdk into flyte-v2-knowledge.json.

Usage: python scripts/build_knowledge.py --sdk-path /path/to/flyte-sdk --out src/flyte_mcp/data/flyte-v2-knowledge.json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path

EXAMPLE_FILE_LIMIT = 6
SNIPPET_LINES = 60


@dataclass
class Symbol:
    name: str
    kind: str
    module: str
    signature: str = ""
    doc: str = ""
    bases: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    params: list[dict] = field(default_factory=list)


@dataclass
class Pattern:
    theme: str
    path: str
    readme: str = ""
    files: list[dict] = field(default_factory=list)


def load_module_ast(file: Path) -> ast.Module:
    return ast.parse(file.read_text(encoding="utf-8"), filename=str(file))


def resolve_reexports(pkg_init: Path) -> dict[str, Path]:
    """Map exported name -> file that defines it (following `from .x import Y`)."""
    tree = load_module_ast(pkg_init)
    pkg_dir = pkg_init.parent
    mapping: dict[str, Path] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.level >= 1:
            target = pkg_dir / (node.module.replace(".", "/") + ".py")
            if not target.exists():
                target = pkg_dir / node.module.replace(".", "/") / "__init__.py"
            if not target.exists():
                continue
            for alias in node.names:
                mapping[alias.asname or alias.name] = target
    return mapping


def get_all_list(pkg_init: Path) -> list[str]:
    tree = load_module_ast(pkg_init)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                    return [
                        el.value for el in node.value.elts
                        if isinstance(el, ast.Constant) and isinstance(el.value, str)
                    ]
    return []


def unparse_sig(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    try:
        sig = ast.unparse(node.args)
    except Exception:
        sig = "..."
    prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
    ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix}{node.name}({sig}){ret}"


def extract_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict]:
    out = []
    args = node.args
    defaults = list(args.defaults)
    total = len(args.args)
    offset = total - len(defaults)
    for i, a in enumerate(args.args):
        if a.arg == "self":
            continue
        default = None
        if i >= offset:
            try:
                default = ast.unparse(defaults[i - offset])
            except Exception:
                default = None
        annot = ast.unparse(a.annotation) if a.annotation else None
        out.append({"name": a.arg, "type": annot, "default": default})
    for kw, dflt in zip(args.kwonlyargs, args.kw_defaults):
        annot = ast.unparse(kw.annotation) if kw.annotation else None
        default = ast.unparse(dflt) if dflt else None
        out.append({"name": kw.arg, "type": annot, "default": default, "kwonly": True})
    return out


def extract_symbol(name: str, file: Path, sdk_src: Path, _depth: int = 0) -> Symbol | None:
    if _depth > 3:
        return None
    try:
        module_rel = str(file.relative_to(sdk_src))
    except ValueError:
        module_rel = str(file)
    tree = load_module_ast(file)
    # Follow re-exports if this file is an __init__.py
    if file.name == "__init__.py":
        pkg_dir = file.parent
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module and node.level >= 1:
                if not any((a.asname or a.name) == name for a in node.names):
                    continue
                target = pkg_dir / (node.module.replace(".", "/") + ".py")
                if not target.exists():
                    target = pkg_dir / node.module.replace(".", "/") / "__init__.py"
                if target.exists():
                    orig = next((a.name for a in node.names if (a.asname or a.name) == name), name)
                    sym = extract_symbol(orig, target, sdk_src, _depth + 1)
                    if sym:
                        sym.name = name
                        return sym
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return Symbol(
                name=name,
                kind="function",
                module=module_rel,
                signature=unparse_sig(node),
                doc=(ast.get_docstring(node) or "").strip(),
                decorators=[ast.unparse(d) for d in node.decorator_list],
                params=extract_params(node),
            )
        if isinstance(node, ast.ClassDef) and node.name == name:
            bases = [ast.unparse(b) for b in node.bases]
            init = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
            params = extract_params(init) if init else []
            sig = f"class {name}({', '.join(bases)})"
            return Symbol(
                name=name,
                kind="class",
                module=module_rel,
                signature=sig,
                doc=(ast.get_docstring(node) or "").strip(),
                bases=bases,
                params=params,
            )
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return Symbol(
                        name=name,
                        kind="constant",
                        module=module_rel,
                        signature=f"{name} = {ast.unparse(node.value)[:120]}",
                    )
    return None


def build_symbols(sdk_src: Path) -> dict[str, dict]:
    pkg_init = sdk_src / "flyte" / "__init__.py"
    all_names = get_all_list(pkg_init)
    reexports = resolve_reexports(pkg_init)
    out: dict[str, dict] = {}
    for name in all_names:
        file = reexports.get(name)
        if not file:
            continue
        sym = extract_symbol(name, file, sdk_src)
        if sym:
            out[f"flyte.{name}"] = asdict(sym)
    return out


def extract_file_snippet(py: Path) -> dict:
    text = py.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    doc = ""
    try:
        tree = ast.parse(text)
        doc = (ast.get_docstring(tree) or "").strip()
    except SyntaxError:
        pass
    return {
        "file": py.name,
        "doc": doc[:400],
        "snippet": "\n".join(lines[:SNIPPET_LINES]),
    }


def build_patterns(examples_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for item in sorted(examples_dir.iterdir()):
        if not item.is_dir() or item.name.startswith((".", "_")):
            continue
        readme = ""
        for rn in ("README.md", "readme.md"):
            rp = item / rn
            if rp.exists():
                readme = rp.read_text(encoding="utf-8", errors="replace")
                break
        py_files = sorted(item.glob("*.py"))[:EXAMPLE_FILE_LIMIT]
        pat = Pattern(
            theme=item.name,
            path=f"examples/{item.name}",
            readme=readme[:2000],
            files=[extract_file_snippet(p) for p in py_files],
        )
        out[item.name] = asdict(pat)
    return out


def read_version(sdk_path: Path) -> str:
    vfile = sdk_path / "src" / "flyte" / "_version.py"
    if vfile.exists():
        m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)", vfile.read_text())
        if m:
            return m.group(1)
    return "unknown"


def read_meta_docs(sdk_path: Path) -> dict:
    out = {}
    for key, name in (("readme", "README.md"), ("features", "FEATURES.md"), ("contributing", "CONTRIBUTING.md")):
        f = sdk_path / name
        if f.exists():
            out[key] = f.read_text(encoding="utf-8", errors="replace")
    return out


def capture_cli_help(sdk_path: Path) -> dict:
    """Try to run `flyte --help` from the SDK's own venv to capture CLI surface."""
    out: dict[str, str] = {}
    candidates = [
        sdk_path / ".venv" / "bin" / "flyte",
        Path("/home/ahlert/Dev/flyte/flyte-sdk/.venv/bin/flyte"),
    ]
    flyte_bin = next((c for c in candidates if c.exists()), None)
    if not flyte_bin:
        return out
    for cmd in (["--help"], ["run", "--help"], ["deploy", "--help"], ["config", "--help"]):
        try:
            r = subprocess.run([str(flyte_bin), *cmd], capture_output=True, text=True, timeout=10)
            out[" ".join(["flyte", *cmd])] = (r.stdout + r.stderr)[:4000]
        except (OSError, subprocess.SubprocessError):
            pass
    return out


def load_plugin_registry(registry_path: Path | None) -> list[dict]:
    if not registry_path or not registry_path.exists():
        return []
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("plugins", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sdk-path", required=True, type=Path)
    p.add_argument("--registry", type=Path, help="Optional path to flyte-plugin-registry plugins.json")
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    sdk_src = args.sdk_path / "src"
    examples = args.sdk_path / "examples"

    data = {
        "sdk_version": read_version(args.sdk_path),
        "sdk_path": str(args.sdk_path),
        "symbols": build_symbols(sdk_src),
        "patterns": build_patterns(examples),
        "meta": read_meta_docs(args.sdk_path),
        "cli": capture_cli_help(args.sdk_path),
        "plugins": load_plugin_registry(args.registry),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(
        f"Wrote {args.out} | symbols={len(data['symbols'])} "
        f"patterns={len(data['patterns'])} plugins={len(data['plugins'])} "
        f"cli={len(data['cli'])}"
    )


if __name__ == "__main__":
    main()
