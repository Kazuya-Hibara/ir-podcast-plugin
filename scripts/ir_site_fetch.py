"""IR site direct PDF fetcher.

Manifest JSON (output of ir-source-discovery agent) を入力に、各 source の URL から
PDF を直接 download する。EDINET / EDGAR API key 不要 — 公開 IR サイトのみ。

Manifest schema:
    {
      "ticker": "4751",
      "company": "...",
      "sources": [
        {"type": "kessan-tanshin-q1", "date": "2026-...", "url": "https://...pdf",
         "title": "...", "size_estimate_kb": 584}
      ]
    }
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import httpx


DEFAULT_UA = "IR-Podcast-Plugin (research; +https://github.com/)"


def _safe_filename(source: dict, idx: int) -> str:
    """Build deterministic filename from source metadata."""
    parts = [
        source.get("date", "").replace("-", "")[:8] or f"doc{idx:02d}",
        re.sub(r"[^a-zA-Z0-9_-]", "_", source.get("type", "ir"))[:32],
    ]
    return "-".join(p for p in parts if p) + ".pdf"


def fetch_pdf(url: str, dest: Path, ua: str, timeout: float = 60.0) -> int:
    """Download URL to dest. Returns bytes written."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers={"User-Agent": ua}, follow_redirects=True, timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    return len(resp.content)


def fetch_manifest(
    manifest_path: Path,
    output_dir: Path,
    no_cache: bool = False,
    ua: str = DEFAULT_UA,
) -> list[Path]:
    """Download all PDFs listed in manifest. Returns list of saved paths."""
    manifest = json.loads(manifest_path.read_text())
    sources = manifest.get("sources") or []
    if not sources:
        raise RuntimeError(f"No sources in manifest: {manifest_path}")

    ticker = manifest.get("ticker", "unknown")
    target_dir = output_dir / ticker
    saved: list[Path] = []

    for idx, src in enumerate(sources):
        url = src.get("url")
        if not url or not url.lower().endswith(".pdf"):
            print(f"skip [{idx}] non-pdf url: {url!r}", file=sys.stderr)
            continue

        dest = target_dir / _safe_filename(src, idx)
        if dest.exists() and not no_cache:
            print(f"cached: {dest} ({dest.stat().st_size} bytes)", file=sys.stderr)
            saved.append(dest)
            continue

        try:
            n = fetch_pdf(url, dest, ua=ua)
            print(f"saved: {dest} ({n} bytes) <- {url}", file=sys.stderr)
            saved.append(dest)
        except httpx.HTTPError as exc:
            print(f"FAIL [{idx}] {url}: {exc}", file=sys.stderr)

    return saved


def main() -> int:
    parser = argparse.ArgumentParser(description="IR site direct PDF fetcher (no API key)")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to manifest JSON (output of ir-source-discovery agent)",
    )
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        help="Single PDF URL (repeatable). For ad-hoc fetch without manifest.",
    )
    parser.add_argument(
        "--ticker",
        help="Ticker / 証券コード (used as output sub-dir when --url is used)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./downloads"),
        help="Base output dir (PDFs saved to <dir>/<ticker>/)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Re-download even if cached file exists",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_UA,
        help="HTTP User-Agent header (default: research-friendly identifier)",
    )
    args = parser.parse_args()

    if args.manifest:
        if not args.manifest.exists():
            sys.stderr.write(f"ERROR: manifest not found: {args.manifest}\n")
            return 1
        saved = fetch_manifest(
            args.manifest, args.output_dir, no_cache=args.no_cache, ua=args.user_agent
        )
    elif args.url:
        if not args.ticker:
            parser.error("--ticker is required when using --url")
        target_dir = args.output_dir / args.ticker
        saved = []
        for idx, url in enumerate(args.url):
            dest = target_dir / _safe_filename({"type": f"doc{idx}"}, idx)
            if dest.exists() and not args.no_cache:
                print(f"cached: {dest}", file=sys.stderr)
                saved.append(dest)
                continue
            try:
                n = fetch_pdf(url, dest, ua=args.user_agent)
                print(f"saved: {dest} ({n} bytes)", file=sys.stderr)
                saved.append(dest)
            except httpx.HTTPError as exc:
                print(f"FAIL {url}: {exc}", file=sys.stderr)
    else:
        parser.error("either --manifest or --url is required")

    print(f"done: {len(saved)} files")
    return 0 if saved else 1


if __name__ == "__main__":
    sys.exit(main())
