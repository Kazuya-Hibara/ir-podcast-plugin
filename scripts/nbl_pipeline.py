"""NotebookLM end-to-end pipeline orchestrator (stub).

`notebooklm` CLI (pip install notebooklm-py) を subprocess で呼ぶ thin wrapper。
SKILL.md `ir-podcast` の Step 5-7 を Python 側からも単発実行可能にする。

実装 TODO. 後続セッションで /autopilot 委譲予定。

公式 CLI docs: https://github.com/teng-lin/notebooklm-py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


NBL_BIN = "notebooklm"  # CLI installed via `pip install notebooklm-py`


def run_nbl(args: list[str], capture: bool = True) -> str:
    """notebooklm CLI を subprocess 実行.

    Returns: stdout (capture=True 時)

    TODO: implement
    1. subprocess.run([NBL_BIN, *args], capture_output=capture, text=True, check=False)
    2. if returncode != 0: raise RuntimeError with stderr
    3. return stdout.strip()
    """
    raise NotImplementedError("run_nbl: stub")


def auth_check() -> bool:
    """`notebooklm auth check --test` で cookie auth が live か確認.

    Returns: True if authenticated.

    TODO: implement
    1. result = subprocess.run([NBL_BIN, 'auth', 'check', '--test'], capture_output=True)
    2. parse result.stdout for 'authenticated: true' or similar
    3. return bool
    """
    raise NotImplementedError("auth_check: stub")


def create_notebook(title: str) -> str:
    """新しい notebook を作成し ID を返す.

    TODO: implement
    1. out = run_nbl(['create', '-t', title, '--json'])
    2. return json.loads(out)['id']
    """
    raise NotImplementedError("create_notebook: stub")


def add_sources(notebook_id: str, files: list[Path]) -> None:
    """複数 source file を notebook に追加し、indexing 完了を待つ.

    TODO: implement
    1. for each f: run_nbl(['source', 'add', '-n', notebook_id, '-f', str(f)])
    2. run_nbl(['source', 'wait', '-n', notebook_id])
    """
    raise NotImplementedError("add_sources: stub")


def generate_audio(notebook_id: str, lang: str = "en") -> None:
    """Audio Overview 生成をリクエストし、完了を待つ.

    Args:
        lang: 'en' / 'ja' / etc.

    TODO: implement
    1. run_nbl(['generate', 'audio', '-n', notebook_id, '--lang', lang])
    2. run_nbl(['artifact', 'wait', '-n', notebook_id, '--type', 'audio'])
    """
    raise NotImplementedError("generate_audio: stub")


def download_audio(notebook_id: str, output_path: Path) -> Path:
    """Audio file を local に download.

    TODO: implement
    1. output_path.parent.mkdir(parents=True, exist_ok=True)
    2. run_nbl(['download', '-n', notebook_id, '--type', 'audio', '-o', str(output_path)])
    3. return output_path
    """
    raise NotImplementedError("download_audio: stub")


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
