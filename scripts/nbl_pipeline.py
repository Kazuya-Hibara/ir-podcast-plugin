"""NotebookLM end-to-end pipeline orchestrator (stub).

`notebooklm` CLI (pip install notebooklm-py) を subprocess で呼ぶ thin wrapper。
SKILL.md `ir-podcast` の Step 5-7 を Python 側からも単発実行可能にする。

実装 TODO. 後続セッションで /autopilot 委譲予定。

公式 CLI docs: https://github.com/teng-lin/notebooklm-py
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _resolve_nbl_bin() -> str:
    """Locate `notebooklm` CLI. Try in order: venv neighbor → $PATH → ~/.local/bin (pipx default)."""
    candidate = Path(sys.executable).parent / "notebooklm"
    if candidate.exists():
        return str(candidate)
    found = shutil.which("notebooklm")
    if found:
        return found
    pipx_path = Path.home() / ".local" / "bin" / "notebooklm"
    if pipx_path.exists():
        return str(pipx_path)
    return "notebooklm"


NBL_BIN = _resolve_nbl_bin()


def run_nbl(args: list[str], capture: bool = True) -> str:
    """notebooklm CLI を subprocess 実行.

    Returns: stdout (capture=True 時)
    """
    if capture:
        result = subprocess.run(
            [NBL_BIN, *args], capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"notebooklm CLI failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return result.stdout.strip()
    else:
        result = subprocess.run([NBL_BIN, *args], check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"notebooklm CLI failed (exit {result.returncode})"
            )
        return ""


def auth_check() -> bool:
    """`notebooklm auth check --test` で cookie auth が live か確認.

    Returns: True if authenticated.
    """
    try:
        result = subprocess.run(
            [NBL_BIN, "auth", "check", "--test"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "notebooklm CLI not found. Run: pip install notebooklm-py>=0.3.4"
        )
    if result.returncode != 0:
        return False
    return "authenticated: true" in result.stdout or result.returncode == 0


def _extract_id(stdout: str, *outer_keys: str) -> str:
    """Parse id from CLI JSON output. Handles three envelope shapes:

    - `{"<outer>": {"id": "..."}}` (nested object)
    - `{"id": "..."}` (top-level id)
    - `{"<outer>_id": "..."}` (flat snake_case, e.g. `{"task_id": "..."}`)
    """
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Non-JSON CLI output: {stdout}")
    original = data
    for key in outer_keys:
        if isinstance(data, dict) and key in data and isinstance(data[key], dict):
            data = data[key]
            break
    if isinstance(data, dict) and "id" in data:
        return data["id"]
    if isinstance(original, dict):
        for key in outer_keys:
            flat = f"{key}_id"
            if flat in original and isinstance(original[flat], str):
                return original[flat]
    raise RuntimeError(f"No id in CLI output: {stdout}")


def create_notebook(title: str) -> str:
    """新しい notebook を作成し ID を返す."""
    return _extract_id(run_nbl(["create", title, "--json"]), "notebook")


def _mime_for(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".html": "text/html",
        ".htm": "text/html",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }.get(ext, "application/octet-stream")


def add_sources(notebook_id: str, files: list[Path]) -> None:
    """複数 source file を notebook に追加し、indexing 完了を待つ."""
    for f in files:
        stdout = run_nbl([
            "source", "add", str(f),
            "-n", notebook_id,
            "--type", "file",
            "--mime-type", _mime_for(f),
            "--json",
        ])
        source_id = _extract_id(stdout, "source")
        run_nbl(["source", "wait", source_id, "-n", notebook_id, "--timeout", "600"])


def _trigger_audio(notebook_id: str, lang: str = "en") -> str:
    """Trigger Audio Overview generation, return task_id (no wait)."""
    stdout = run_nbl([
        "generate", "audio",
        "-n", notebook_id,
        "--language", lang,
        "--json",
    ])
    return _extract_id(stdout, "task", "artifact", "audio")


def _wait_audio(notebook_id: str, task_id: str, timeout: int = 1800) -> None:
    """Block until artifact is ready. CLI internal timeout is 300s, override here."""
    run_nbl(
        ["artifact", "wait", task_id, "-n", notebook_id, "--timeout", str(timeout)],
        capture=False,
    )


def generate_audio(notebook_id: str, lang: str = "en") -> None:
    """Compatibility wrapper: trigger + wait. Prefer _trigger_audio + _wait_audio for resumable flows."""
    task_id = _trigger_audio(notebook_id, lang=lang)
    _wait_audio(notebook_id, task_id)


def download_audio(notebook_id: str, output_path: Path) -> Path:
    """Audio file を local に download."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_nbl(["download", "audio", str(output_path), "-n", notebook_id, "--latest", "--force"])
    return output_path


def _state_path(output: Path) -> Path:
    """Sibling state file: <output>.state.json (e.g. AAPL-...mp3.state.json)."""
    return output.with_suffix(output.suffix + ".state.json")


def _load_state(output: Path) -> dict:
    p = _state_path(output)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(output: Path, **kwargs) -> None:
    p = _state_path(output)
    state = _load_state(output)
    state.update(kwargs)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2))


def pipeline(
    title: str,
    sources: list[Path],
    lang: str,
    output_path: Path,
    resume: bool = False,
) -> Path:
    """End-to-end pipeline: create → add → trigger → wait → download.

    State persisted to <output>.state.json after each milestone. With resume=True,
    skips already-completed steps. State file removed on success.

    Returns: path to downloaded audio file.
    """
    if not auth_check():
        sys.stderr.write(
            "ERROR: NotebookLM not authenticated. Run: notebooklm login\n"
        )
        sys.exit(1)

    state = _load_state(output_path) if resume else {}

    notebook_id = state.get("notebook_id")
    if notebook_id:
        print(f"Resumed notebook: {notebook_id}", file=sys.stderr)
    else:
        notebook_id = create_notebook(title)
        _save_state(output_path, notebook_id=notebook_id)
        print(f"Created notebook: {notebook_id}", file=sys.stderr)

    if state.get("sources_added"):
        print("Sources already added (resumed)", file=sys.stderr)
    else:
        add_sources(notebook_id, sources)
        _save_state(output_path, sources_added=True)
        print(f"Added {len(sources)} sources", file=sys.stderr)

    task_id = state.get("task_id")
    if task_id:
        print(f"Resumed audio task: {task_id}", file=sys.stderr)
    else:
        task_id = _trigger_audio(notebook_id, lang=lang)
        _save_state(output_path, task_id=task_id)
        print(f"Audio task triggered: {task_id}", file=sys.stderr)

    _wait_audio(notebook_id, task_id)
    print("Audio generated", file=sys.stderr)

    audio_path = download_audio(notebook_id, output_path)
    print(f"Downloaded: {audio_path}", file=sys.stderr)

    # Cleanup state on success (subsequent runs start fresh unless --resume re-attaches)
    state_file = _state_path(output_path)
    if state_file.exists():
        state_file.unlink()

    return audio_path


def main() -> int:
    parser = argparse.ArgumentParser(description="NotebookLM pipeline orchestrator")
    parser.add_argument("--title", required=True, help="Notebook title")
    parser.add_argument(
        "--sources",
        nargs="+",
        required=True,
        type=Path,
        help="Source file paths (PDF/MD/HTML)",
    )
    parser.add_argument("--lang", default="en", help="Audio Overview language (default: en)")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output audio file path (.wav)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Pre-flight auth check only",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from <output>.state.json if present (skip already-completed steps)",
    )
    args = parser.parse_args()

    if args.check:
        ok = auth_check()
        print("authenticated" if ok else "NOT authenticated (run: notebooklm login)")
        return 0 if ok else 1

    for s in args.sources:
        if not s.exists():
            sys.stderr.write(f"ERROR: source not found: {s}\n")
            return 1

    pipeline(args.title, args.sources, args.lang, args.output, resume=args.resume)
    return 0


if __name__ == "__main__":
    sys.exit(main())
