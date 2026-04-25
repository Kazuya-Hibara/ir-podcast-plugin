"""TDnet (適時開示) PDF fetcher for JP-listed companies.

Default JP path. No auth, no API key — uses yanoshin webapi
(https://webapi.yanoshin.jp/) as the practical wrapper around the
official TDnet site (https://www.release.tdnet.info/).

⚠️ TDnet retention limit: PDF は **概ね 30 日で release.tdnet.info から削除** される。
yanoshin の disclosures 一覧は 1 年以上残っているが PDF DL は最近のみ。
古い 決算短信 / 有価証券報告書 が必要なら:
  - 各社 IR ページを Firecrawl skill で scrape (`agents/ir-source-discovery.md`)
  - or `scripts/edinet_fetch.py` (要 EDINET API key、無料申請)

Quick reference:
  python3 scripts/tdnet_fetch.py --code 7203 --types kessan-tanshin --depth quick
  python3 scripts/tdnet_fetch.py --code 6758 --depth deep --output-dir ./downloads/6758
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx


YANOSHIN_BASE = "https://webapi.yanoshin.jp/webapi/tdnet"
RATE_LIMIT_PER_SEC = 5  # yanoshin の体感安全帯

# release.tdnet.info は default httpx UA を 403 で弾くため browser-like header を送る
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/x-pdf,*/*",
    "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

# 適時開示 doc type → title 内に含まれる typical keywords
DOC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "kessan-tanshin": ["決算短信"],
    "setsumei": ["決算説明", "決算補足", "決算プレゼン"],
    "rinji": ["適時開示", "重要事実"],
    "yuho": ["有価証券報告書"],   # TDnet には EDINET ほど揃わないが念のため
    "shihanki": ["四半期報告書"],
    "all": [],
}


def list_disclosures(code: str, days: int = 365, limit: int = 100) -> list[dict]:
    """ticker (4-digit) → 適時開示 list (newest first).

    yanoshin 側で限度 100 件 / 1 リクエスト。Returns list of Tdnet items.
    """
    code = code.strip().zfill(4)
    url = f"{YANOSHIN_BASE}/list/{code}.json"
    params = {"limit": str(limit), "days": str(days)}
    resp = httpx.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return [item.get("Tdnet", {}) for item in data.get("items", [])]


def filter_by_type(items: list[dict], doc_types: list[str]) -> list[dict]:
    """title keyword で filter. doc_types: ['kessan-tanshin', 'setsumei', ...]."""
    if not doc_types or "all" in doc_types:
        return items
    keywords: list[str] = []
    for t in doc_types:
        keywords.extend(DOC_TYPE_KEYWORDS.get(t, []))
    if not keywords:
        return items
    return [it for it in items if any(kw in it.get("title", "") for kw in keywords)]


def _resolve_pdf_url(yanoshin_url: str) -> str:
    """yanoshin redirect URL を直接 PDF URL に展開."""
    marker = "?https://"
    idx = yanoshin_url.find(marker)
    if idx == -1:
        return yanoshin_url
    return "https://" + yanoshin_url[idx + len(marker):]


def download_pdf(item: dict, output_dir: Path) -> str:
    """Download PDF for a single Tdnet item. Returns local path or empty on skip."""
    doc_url_raw = item.get("document_url") or ""
    if not doc_url_raw:
        return ""
    pdf_url = _resolve_pdf_url(doc_url_raw)
    pubdate = (item.get("pubdate") or "")[:10] or "unknown"
    item_id = item.get("id") or "0"
    target = output_dir / f"{pubdate}-{item_id}.pdf"

    target.parent.mkdir(parents=True, exist_ok=True)
    backoff = 2
    for attempt in range(3):
        try:
            resp = httpx.get(
                pdf_url, timeout=60, follow_redirects=True, headers=_BROWSER_HEADERS
            )
            if resp.status_code == 404:
                sys.stderr.write(f"WARN: 404 {pdf_url}\n")
                return ""
            if resp.status_code in (429, 500, 502, 503, 504):
                if attempt < 2:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            target.write_bytes(resp.content)
            return str(target)
        except httpx.HTTPStatusError:
            if attempt == 2:
                raise
            time.sleep(backoff)
            backoff *= 2
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="TDnet (適時開示) PDF fetcher")
    parser.add_argument("--code", required=True, help="証券コード (4 digits, e.g. 7203)")
    parser.add_argument(
        "--types",
        default="kessan-tanshin,setsumei",
        help=(
            f"Comma-separated doc types (default: kessan-tanshin,setsumei). "
            f"Available: {','.join(DOC_TYPE_KEYWORDS)}"
        ),
    )
    parser.add_argument(
        "--depth",
        choices=("quick", "deep"),
        default="quick",
        help="quick=latest 1 per type / deep=latest 4 per type",
    )
    parser.add_argument("--days", type=int, default=365, help="検索する過去日数 (default: 365)")
    parser.add_argument("--output-dir", default="./downloads", help="Local download dir")
    parser.add_argument("--check", action="store_true", help="Pre-flight only (yanoshin reachability)")
    args = parser.parse_args()

    if args.check:
        try:
            httpx.head(YANOSHIN_BASE + "/list/7203.json", timeout=10)
            print(f"OK: {YANOSHIN_BASE} reachable")
            return 0
        except httpx.HTTPError as exc:
            sys.stderr.write(f"ERROR: yanoshin unreachable: {exc}\n")
            return 1

    doc_types = [t.strip() for t in args.types.split(",") if t.strip()]
    cap_per_type = 1 if args.depth == "quick" else 4

    try:
        items = list_disclosures(args.code, days=args.days, limit=100)
    except httpx.HTTPError as exc:
        sys.stderr.write(f"ERROR: yanoshin list failed: {exc}\n")
        return 1

    filtered = filter_by_type(items, doc_types)

    selected: list[dict]
    if "all" in doc_types:
        # 単純 cap、type 別カウントなし
        selected = filtered[: cap_per_type * max(1, len(doc_types))]
    else:
        selected = []
        counts: dict[str, int] = {t: 0 for t in doc_types}
        for it in filtered:
            title = it.get("title", "")
            for t in doc_types:
                kws = DOC_TYPE_KEYWORDS.get(t, [])
                if any(kw in title for kw in kws):
                    if counts[t] < cap_per_type:
                        selected.append(it)
                        counts[t] += 1
                    break

    if not selected:
        sys.stderr.write(
            f"WARN: no matching disclosures for {args.code} (types={doc_types}).\n"
            f"  TDnet retention is ~30 days; older 決算短信 etc. are removed.\n"
            f"  Try: --types all   or use Firecrawl/EDINET for historical data.\n"
        )
        return 1

    out_dir = Path(args.output_dir)
    saved: list[str] = []
    for it in selected:
        path = download_pdf(it, out_dir)
        if path:
            saved.append(path)
            print(f"saved: {path}  # {it.get('title', '')[:60]}")
        time.sleep(1 / RATE_LIMIT_PER_SEC)

    print(f"done: {len(saved)} files in {out_dir}")
    return 0 if saved else 1


if __name__ == "__main__":
    sys.exit(main())
