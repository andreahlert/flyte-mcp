"""MCP server exposing Flyte V2 SDK knowledge + plugin registry + runtime tools."""
from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import migrate as migrate_mod
from . import runtime as runtime_mod

mcp = FastMCP("flyte")


@lru_cache(maxsize=1)
def knowledge() -> dict:
    data_pkg = resources.files(__package__) / "data" / "flyte-v2-knowledge.json"
    return json.loads(Path(str(data_pkg)).read_text(encoding="utf-8"))


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in text.replace("_", " ").split() if len(t) > 2}


def _score(query: str, *fields: str) -> int:
    q = _tokens(query)
    if not q:
        return 0
    blob = _tokens(" ".join(f or "" for f in fields))
    return len(q & blob)


# ---------------------------------------------------------------------------
# Overview / meta
# ---------------------------------------------------------------------------

@mcp.tool()
def get_flyte_version() -> dict:
    """Flyte SDK version this knowledge pack was built from, plus counts."""
    k = knowledge()
    return {
        "sdk_version": k.get("sdk_version"),
        "symbols": len(k.get("symbols", {})),
        "patterns": len(k.get("patterns", {})),
        "plugins": len(k.get("plugins", [])),
    }


@mcp.tool()
def get_flyte_overview() -> str:
    """Return the flyte-sdk README - high-level description of Flyte V2."""
    return knowledge().get("meta", {}).get("readme", "")


@mcp.tool()
def get_flyte_features() -> str:
    """Return the flyte-sdk FEATURES.md - concise list of V2 capabilities."""
    return knowledge().get("meta", {}).get("features", "")


@mcp.tool()
def get_flyte_install_guide() -> dict:
    """Return CLI help output and install instructions parsed from flyte-sdk."""
    k = knowledge()
    return {
        "cli_help": k.get("cli", {}),
        "install_hint": "pip install flyte   # V2 SDK, requires Python >= 3.10",
        "quickstart": (
            "import flyte\n"
            "env = flyte.TaskEnvironment(name='hello')\n"
            "@env.task\n"
            "async def greet(name: str) -> str:\n"
            "    return f'Hello {name}'\n"
            "if __name__ == '__main__':\n"
            "    flyte.init_from_config()\n"
            "    print(flyte.run(greet, name='world').url)"
        ),
    }


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------

@mcp.tool()
def list_flyte_symbols(kind: str | None = None) -> list[dict]:
    """List public Flyte V2 API symbols. Optional kind filter: function, class, constant."""
    return [
        {"name": name, "kind": s["kind"], "signature": s["signature"]}
        for name, s in knowledge().get("symbols", {}).items()
        if not kind or s["kind"] == kind
    ]


@mcp.tool()
def get_flyte_symbol(name: str) -> dict:
    """Full detail of one Flyte V2 symbol: signature, params, docstring, module path.

    Accepts "flyte.TaskEnvironment" or just "TaskEnvironment".
    """
    syms = knowledge().get("symbols", {})
    key = name if name.startswith("flyte.") else f"flyte.{name}"
    sym = syms.get(key)
    if not sym:
        return {"error": f"not found: {name}", "available": list(syms.keys())[:20]}
    return sym


@mcp.tool()
def search_flyte_api(query: str, limit: int = 5) -> list[dict]:
    """Keyword search over Flyte V2 symbol names, signatures, docstrings."""
    ranked = []
    for name, s in knowledge().get("symbols", {}).items():
        score = _score(query, name, s.get("signature", ""), s.get("doc", ""))
        if score:
            ranked.append((score, {
                "name": name,
                "kind": s["kind"],
                "signature": s["signature"],
                "doc": s.get("doc", "")[:200],
            }))
    ranked.sort(key=lambda x: -x[0])
    return [r[1] for r in ranked[:limit]]


# ---------------------------------------------------------------------------
# Example patterns
# ---------------------------------------------------------------------------

@mcp.tool()
def list_flyte_patterns() -> list[dict]:
    """Canonical example themes from flyte-sdk/examples/."""
    return [
        {"theme": t, "path": p["path"], "files": [f["file"] for f in p["files"]]}
        for t, p in knowledge().get("patterns", {}).items()
    ]


@mcp.tool()
def get_flyte_pattern(theme: str, file: str | None = None) -> dict:
    """Return README and example code for a theme (e.g. 'caching', 'genai', 'accelerators').

    If file is given, return just that file's snippet. Otherwise README + first file.
    """
    p = knowledge().get("patterns", {}).get(theme)
    if not p:
        return {"error": f"theme not found: {theme}", "available": list(knowledge().get("patterns", {}).keys())}
    if file:
        match = next((f for f in p["files"] if f["file"] == file), None)
        if not match:
            return {"error": f"file not found in {theme}: {file}", "available": [f["file"] for f in p["files"]]}
        return {"theme": theme, "path": p["path"], "file": match}
    return p


@mcp.tool()
def find_flyte_example_for(use_case: str, limit: int = 3) -> list[dict]:
    """Find example themes best matching a natural-language use case.

    Searches READMEs and file docstrings across all example themes.
    """
    ranked = []
    for theme, p in knowledge().get("patterns", {}).items():
        blob = p.get("readme", "") + " " + " ".join(f.get("doc", "") for f in p["files"])
        score = _score(use_case, theme, blob)
        if score:
            ranked.append((score, {
                "theme": theme,
                "path": p["path"],
                "summary": (p.get("readme", "") or "").strip().split("\n")[0][:200],
            }))
    ranked.sort(key=lambda x: -x[0])
    return [r[1] for r in ranked[:limit]]


# ---------------------------------------------------------------------------
# Plugin registry (from flyte-plugin-registry)
# ---------------------------------------------------------------------------

@mcp.tool()
def list_flyte_plugins(category: str | None = None) -> list[dict]:
    """List Flyte plugins from the registry. Optional category filter."""
    plugins = knowledge().get("plugins", [])
    if category:
        plugins = [p for p in plugins if p.get("category") == category]
    return [
        {
            "slug": p.get("slug"),
            "name": p.get("name"),
            "package": p.get("packageName"),
            "category": p.get("category"),
            "install": p.get("installCommand") or f"pip install {p.get('packageName', '')}",
            "sdk": p.get("sdk"),
            "deprecated": p.get("isDeprecated", False),
        }
        for p in plugins
    ]


@mcp.tool()
def get_flyte_plugin(slug: str) -> dict:
    """Full detail of a Flyte plugin by slug: package, modules, versions, install command."""
    for p in knowledge().get("plugins", []):
        if p.get("slug") == slug or p.get("packageName") == slug:
            return p
    return {"error": f"plugin not found: {slug}"}


@mcp.tool()
def suggest_flyte_plugin_for(need: str, limit: int = 5) -> list[dict]:
    """Given a natural-language need (e.g. 'run Spark', 'connect Snowflake'), suggest plugins.

    Prefers V2-native entries (sdk='flyte-sdk') over legacy V1 duplicates.
    """
    ranked = []
    for p in knowledge().get("plugins", []):
        name_score = _score(need, p.get("name", ""), p.get("slug", ""))
        body_score = _score(need, p.get("description", ""), str(p.get("tags", "")), p.get("category", ""))
        score = name_score * 5 + body_score
        if score == 0:
            continue
        if p.get("sdk") == "flyte-sdk":
            score += 2
        if p.get("isDeprecated"):
            score -= 3
        ranked.append((score, {
            "slug": p.get("slug"),
            "name": p.get("name"),
            "package": p.get("packageName"),
            "sdk": p.get("sdk"),
            "description": (p.get("description") or "")[:200],
            "install": p.get("installCommand") or f"pip install {p.get('packageName', '')}",
        }))
    ranked.sort(key=lambda x: -x[0])
    return [r[1] for r in ranked[:limit]]


# ---------------------------------------------------------------------------
# V1 -> V2 migration
# ---------------------------------------------------------------------------

@mcp.tool()
def migrate_v1_to_v2(code: str) -> dict:
    """Rewrite flytekit V1 Python code into flyte-sdk V2 syntax.

    Returns the transformed code plus a list of applied changes and warnings
    about patterns that need manual review.
    """
    result = migrate_mod.migrate(code)
    return {"code": result.code, "changes": result.changes, "warnings": result.warnings}


# ---------------------------------------------------------------------------
# Runtime (optional - requires flyte-sdk installed + configured)
# ---------------------------------------------------------------------------

@mcp.tool()
def run_flyte_task(module_path: str, task_name: str, inputs: dict | None = None) -> dict:
    """Execute a task on the configured Flyte cluster. Requires flyte-sdk installed.

    module_path: absolute path to the .py file defining the task
    task_name:   Python name of the task function within that file
    inputs:      dict of input kwargs
    """
    return runtime_mod.run_task(module_path, task_name, inputs)


@mcp.tool()
def get_flyte_execution_status(run_id: str) -> dict:
    """Fetch current status of a Flyte run by id."""
    return runtime_mod.get_execution_status(run_id)


@mcp.tool()
def list_flyte_recent_runs(limit: int = 10) -> list[dict]:
    """List recent runs from the configured Flyte cluster."""
    return runtime_mod.list_recent_runs(limit)


# ---------------------------------------------------------------------------

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
