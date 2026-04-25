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
    """Locate `notebooklm` CLI. Prefer venv neighbor of sys.executable, else $PATH."""
    candidate = Path(sys.executable).parent / "notebooklm"
    if candidate.exists():
        return str(candidate)
    found = shutil.which("notebooklm")
    return found or "notebooklm"


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
    """Parse `{"<outer>": {"id": "..."}}` or `{"id": "..."}` JSON envelope."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Non-JSON CLI output: {stdout}")
    for key in outer_keys:
        if isinstance(data, dict) and key in data and isinstance(data[key], dict):
            data = data[key]
            break
    if isinstance(data, dict) and "id" in data:
        return data["id"]
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


def generate_audio(notebook_id: str, lang: str = "en") -> None:
    """Audio Overview 生成をリクエストし、完了を待つ.

    `--wait` で blocking 実行 (10-30 min). capture=False で progress を user に流す.
    """
    run_nbl(
        ["generate", "audio", "-n", notebook_id, "--language", lang, "--wait"],
        capture=False,
    )


def download_audio(notebook_id: str, output_path: Path) -> Path:
    """Audio file を local に download."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_nbl(["download", "audio", str(output_path), "-n", notebook_id, "--latest", "--force"])
    return output_path


def pipeline(
    title: str,
    sources: list[Path],
    lang: str,
    output_path: Path,
) -> Path:
    """End-to-end pipeline: create → add → generate → download.

    Returns: path to downloaded audio file.
    """
    if not auth_check():
        sys.stderr.write(
            "ERROR: NotebookLM not authenticated. Run: notebooklm login\n"
        )
        sys.exit(1)

    notebook_id = create_notebook(title)
    print(f"Created notebook: {notebook_id}", file=sys.stderr)

    add_sources(notebook_id, sources)
    print(f"Added {len(sources)} sources", file=sys.stderr)

    generate_audio(notebook_id, lang=lang)
    print("Audio generated", file=sys.stderr)

    audio_path = download_audio(notebook_id, output_path)
    print(f"Downloaded: {audio_path}", file=sys.stderr)

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
    args = parser.parse_args()

    if args.check:
        ok = auth_check()
        print("authenticated" if ok else "NOT authenticated (run: notebooklm login)")
        return 0 if ok else 1

    for s in args.sources:
        if not s.exists():
            sys.stderr.write(f"ERROR: source not found: {s}\n")
            return 1

    pipeline(args.title, args.sources, args.lang, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
