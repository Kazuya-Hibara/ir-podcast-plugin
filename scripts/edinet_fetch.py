"""EDINET API client (stub).

実装 TODO. 後続セッションで /autopilot 委譲予定。

公式 docs:
- https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0110.html
- API: https://api.edinet-fsa.go.jp/api/v2/

API key 取得: https://disclosure2.edinet-fsa.go.jp の利用申請から (無料)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx


API_KEY_ENV = "EDINET_API_KEY"
EDINET_BASE = "https://api.edinet-fsa.go.jp/api/v2"

# docTypeCode reference (https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0110.html)
DOC_TYPES = {
    "yuho": "120",          # 有価証券報告書
    "shihanki": "140",      # 四半期報告書
    "hanki": "160",         # 半期報告書
    "rinji": "180",         # 臨時報告書
    "kessan-tanshin": "350",  # 決算短信 (注: TDnet 経由が main、EDINET には全件来ない)
}


def check_api_key() -> str:
    key = os.environ.get(API_KEY_ENV)
    if not key:
        sys.stderr.write(
            f"ERROR: env var {API_KEY_ENV} is required.\n"
            f"  Get one at: https://disclosure2.edinet-fsa.go.jp\n"
            f"  Then: export {API_KEY_ENV}=\"<your-key>\"\n"
        )
        sys.exit(1)
    return key


def list_documents_for_date(date: str, api_key: str) -> list[dict]:
    """指定日に提出された書類一覧を取得.

    Args:
        date: 'YYYY-MM-DD'
    """
    url = f"{EDINET_BASE}/documents.json"
    params = {"date": date, "type": "2", "Subscription-Key": api_key}
    resp = httpx.get(url, params=params)
    resp.raise_for_status()
    return resp.json().get("results", []) or []


def filter_by_company(
    documents: list[dict],
    sec_code: str | None = None,
    edinet_code: str | None = None,
    doc_types: list[str] | None = None,
) -> list[dict]:
    """銘柄コード or EDINET コードで filter."""
    result = documents
    if sec_code:
        padded = sec_code + "0" if len(sec_code) == 4 else sec_code
        result = [d for d in result if d.get("secCode") in (sec_code, padded)]
    if edinet_code:
        result = [d for d in result if d.get("edinetCode") == edinet_code]
    if doc_types:
        codes = {DOC_TYPES[t] for t in doc_types if t in DOC_TYPES}
        result = [d for d in result if d.get("docTypeCode") in codes]
    return sorted(result, key=lambda d: d.get("submitDateTime", ""), reverse=True)


def download_document(doc_id: str, output_path: str, api_key: str, doc_type: int = 1) -> str:
    """書類 PDF / XBRL を download.

    Args:
        doc_id: documents.json の docID
        doc_type: 1=PDF, 2=XBRL, 3=ZIP, 4=英文, 5=サマリ
    """
    url = f"{EDINET_BASE}/documents/{doc_id}"
    params = {"type": doc_type, "Subscription-Key": api_key}
    resp = httpx.get(url, params=params)
    if resp.status_code == 404:
        sys.stderr.write(f"WARN: {doc_id} not found (取下げ済みの可能性)\n")
        return ""
    resp.raise_for_status()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(resp.content)
    return str(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="EDINET documents fetcher")
    parser.add_argument("--code", help="証券コード (4 digits, e.g., 7203)")
    parser.add_argument("--edinet-code", help="EDINET 提出者コード (E XXXXX 形式)")
    parser.add_argument(
        "--types",
        default="yuho,shihanki",
        help=f"Comma-separated doc types (default: yuho,shihanki). Available: {','.join(DOC_TYPES)}",
    )
    parser.add_argument(
        "--depth",
        choices=("quick", "deep"),
        default="quick",
        help="quick=latest 1 per type / deep=latest 4 per type",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=730,
        help="検索する過去日数 (default: 730 = 約 2 年)",
    )
    parser.add_argument(
        "--output-dir",
        default="./downloads",
        help="Local download directory (default: ./downloads)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Pre-flight check (env vars) only, no fetch",
    )
    args = parser.parse_args()

    api_key = check_api_key()

    if args.check:
        print(f"OK: {API_KEY_ENV}=<masked, {len(api_key)} chars>")
        return 0

    if not (args.code or args.edinet_code):
        parser.error("either --code or --edinet-code is required")

    doc_types = [t.strip() for t in args.types.split(",") if t.strip()]
    cap_per_type = 1 if args.depth == "quick" else 4
    matched: list[dict] = []
    counts: dict[str, int] = {DOC_TYPES[t]: 0 for t in doc_types if t in DOC_TYPES}

    today = date.today()
    for delta in range(args.days):
        if all(c >= cap_per_type for c in counts.values()) and counts:
            break
        d = (today - timedelta(days=delta)).isoformat()
        try:
            docs = list_documents_for_date(d, api_key)
        except httpx.HTTPStatusError as exc:
            sys.stderr.write(f"WARN: {d} list failed ({exc.response.status_code}), skip\n")
            continue
        if not docs:
            continue
        filtered = filter_by_company(docs, args.code, args.edinet_code, doc_types)
        for doc in filtered:
            code = doc.get("docTypeCode", "")
            if code not in counts or counts[code] >= cap_per_type:
                continue
            matched.append(doc)
            counts[code] += 1

    out_dir = Path(args.output_dir)
    saved: list[str] = []
    for doc in matched:
        doc_id = doc["docID"]
        type_code = doc.get("docTypeCode", "0")
        target = out_dir / f"{doc_id}-{type_code}.pdf"
        path = download_document(doc_id, target, api_key, doc_type=1)
        if path:
            saved.append(path)
            print(f"saved: {path}")
        else:
            sys.stderr.write(f"WARN: {doc_id} not available (404)\n")

    print(f"done: {len(saved)} files in {out_dir}")
    return 0 if saved else 1


if __name__ == "__main__":
    sys.exit(main())
