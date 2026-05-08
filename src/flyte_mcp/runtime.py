"""Optional runtime tools backed by Flyte v2 SDK.

Imports `flyte` lazily so the server runs without the SDK installed.
All functions return structured dicts with `error` when the SDK/config is missing.
"""
from __future__ import annotations

from typing import Any


def _load_remote() -> tuple[Any, Any, str | None]:
    try:
        import flyte  # type: ignore
        from flyte.remote import Run  # type: ignore
    except ImportError:
        return None, None, "flyte-sdk not installed. Install with: pip install flyte"
    try:
        flyte.init_from_config()
    except Exception as e:  # broad: any config failure surfaces as structured error
        return None, None, f"Flyte not configured: {e}. Run `flyte init` or set FLYTE_* env vars."
    return flyte, Run, None


def _phase_name(run: Any) -> str:
    p = getattr(run, "phase", None)
    if p is None:
        return "unknown"
    return getattr(p, "name", None) or str(p)


def run_task(module_path: str, task_name: str, inputs: dict | None = None) -> dict:
    flyte, _Run, err = _load_remote()
    if err:
        return {"error": err}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_user_task", module_path)
        if not spec or not spec.loader:
            return {"error": f"cannot load module: {module_path}"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        task = getattr(mod, task_name, None)
        if task is None:
            return {"error": f"task {task_name!r} not found in {module_path}"}
        run = flyte.run(task, **(inputs or {}))
        return {"run_id": getattr(run, "name", None), "url": getattr(run, "url", None)}
    except Exception as e:
        return {"error": f"run failed: {e}"}


def get_execution_status(run_id: str) -> dict:
    _flyte, Run, err = _load_remote()
    if err:
        return {"error": err}
    try:
        run = Run.get(name=run_id)
        return {
            "run_id": run_id,
            "status": _phase_name(run),
            "url": getattr(run, "url", None),
        }
    except Exception as e:
        return {"error": f"status failed: {e}"}


def list_recent_runs(limit: int = 10) -> list[dict]:
    _flyte, Run, err = _load_remote()
    if err:
        return [{"error": err}]
    try:
        runs = Run.listall(limit=limit)
        return [
            {"run_id": r.name, "status": _phase_name(r), "url": getattr(r, "url", None)}
            for r in runs
        ]
    except Exception as e:
        return [{"error": f"list failed: {e}"}]
