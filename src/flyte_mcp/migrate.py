"""V1 (flytekit) -> V2 (flyte-sdk) code rewriter.

Handles the common cases. Flags edges for manual review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class MigrationResult:
    code: str
    changes: list[str]
    warnings: list[str]


_IMPORT_LINE_RE = re.compile(r"^from flytekit(\.\w+)? import (?P<names>[^\n#]+)", re.MULTILINE)
_IMPORT_BARE_RE = re.compile(r"^import flytekit\b", re.MULTILINE)
_PLUGIN_IMPORT_RE = re.compile(r"\bflytekitplugins\.")


def _rewrite_flytekit_imports(code: str, changes: list[str]) -> str:
    def repl(m: re.Match[str]) -> str:
        names = [n.strip() for n in m.group("names").split(",") if n.strip()]
        kept = [n for n in names if n != "workflow"]
        dropped = [n for n in names if n == "workflow"]
        if dropped:
            changes.append("dropped `workflow` import (V2 workflows are plain async functions)")
        # Always bring TaskEnvironment along when task is imported.
        if "task" in kept and "TaskEnvironment" not in kept:
            kept.append("TaskEnvironment")
        submod = m.group(1) or ""
        if not kept:
            return f"# from flyte{submod} import (removed: workflow no longer exists)"
        new = f"from flyte{submod} import {', '.join(kept)}"
        changes.append(f"{m.group(0)!r} -> {new!r}")
        return new

    return _IMPORT_LINE_RE.sub(repl, code)


def migrate(code: str) -> MigrationResult:
    changes: list[str] = []
    warnings: list[str] = []
    original = code

    code = _rewrite_flytekit_imports(code, changes)

    if _IMPORT_BARE_RE.search(code):
        code = _IMPORT_BARE_RE.sub("import flyte", code)
        changes.append("`import flytekit` -> `import flyte`")

    if _PLUGIN_IMPORT_RE.search(code):
        code = _PLUGIN_IMPORT_RE.sub("flyteplugins.", code)
        changes.append("plugin namespace: `flytekitplugins.*` -> `flyteplugins.*`")

    if re.search(r"\bflytekit\.", code):
        code = re.sub(r"\bflytekit\.", "flyte.", code)
        changes.append("attribute access: `flytekit.*` -> `flyte.*`")

    if re.search(r"^\s*@task\b", code, flags=re.MULTILINE):
        warnings.append(
            "Top-level `@task` found. V2 prefers tasks on a TaskEnvironment: "
            "create `env = flyte.TaskEnvironment(name=\"...\")` and use `@env.task`."
        )

    if re.search(r"^\s*@workflow\b", code, flags=re.MULTILINE):
        code = re.sub(r"^\s*@workflow\s*\n", "", code, flags=re.MULTILINE)
        changes.append("removed `@workflow` decorator (V2 workflows are plain async functions)")

    if re.search(r"Resources\s*\(\s*requests\s*=", code):
        warnings.append(
            "Resources(requests=..., limits=...) kwargs renamed in V2: "
            "use `Resources(cpu=(min, max), memory=(min, max))` tuples instead."
        )

    if re.search(r"^\s*def\s+\w+\([^)]*\)\s*->", code, flags=re.MULTILINE):
        warnings.append(
            "V2 tasks default to `async def`. Convert `def foo(...)` to `async def foo(...)` "
            "for concurrency; sync tasks still work but lose benefits."
        )

    if code == original and not changes:
        warnings.append("No V1 patterns detected - code may already be V2 or not Flyte code.")

    return MigrationResult(code=code, changes=changes, warnings=warnings)
