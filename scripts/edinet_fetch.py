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

    TODO: implement
    1. GET {EDINET_BASE}/documents.json?date={date}&type=2&Subscription-Key={api_key}
    2. parse results, return list of {docID, docTypeCode, edinetCode, secCode, filerName, ...}
    """
    raise NotImplementedError("list_documents_for_date: stub")


def filter_by_company(
    documents: list[dict],
    sec_code: str | None = None,
    edinet_code: str | None = None,
    doc_types: list[str] | None = None,
) -> list[dict]:
    """銘柄コード or EDINET コードで filter.

    TODO: implement
    1. if sec_code: filter docs where secCode == sec_code (注: EDINET は 5 桁の場合あり、4 桁 + '0' 補完が必要なケース)
    2. if edinet_code: filter by edinetCode
    3. if doc_types: filter by docTypeCode in [DOC_TYPES[t] for t in doc_types]
    4. sort by submitDateTime desc
    """
    raise NotImplementedError("filter_by_company: stub")


def download_document(doc_id: str, output_path: str, api_key: str, doc_type: int = 1) -> str:
    """書類 PDF / XBRL を download.

    Args:
        doc_id: documents.json の docID
        doc_type: 1=PDF, 2=XBRL, 3=ZIP, 4=英文, 5=サマリ

    TODO: implement
    1. GET {EDINET_BASE}/documents/{doc_id}?type={doc_type}&Subscription-Key={api_key}
    2. save response body to output_path
    3. handle 404 (書類取下げ) gracefully
    """
    raise NotImplementedError("download_document: stub")


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

    # TODO: 過去 N 日分の documents.json を順に取得 → filter → download
    # NOTE: EDINET API は date 単位の list 取得 + 個別 doc download の 2 段階
    raise NotImplementedError("main pipeline: stub")


if __name__ == "__main__":
    sys.exit(main())
