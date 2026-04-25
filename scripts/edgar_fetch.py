"""SEC EDGAR API client (stub).

実装 TODO. 後続セッションで /autopilot 委譲予定。

公式 docs:
- https://www.sec.gov/edgar/sec-api-documentation
- https://www.sec.gov/os/accessing-edgar-data
"""
from __future__ import annotations

import argparse
import os
import sys


# SEC EDGAR User-Agent ポリシー: <Sample Company Name> AdminContact@<sample company domain>.com
# 違反時は API access ブロック。env var 必須化で safety net 確保
USER_AGENT_ENV = "EDGAR_USER_AGENT"
EDGAR_BASE = "https://data.sec.gov"
RATE_LIMIT_PER_SEC = 10  # https://www.sec.gov/os/accessing-edgar-data


def check_user_agent() -> str:
    ua = os.environ.get(USER_AGENT_ENV)
    if not ua:
        sys.stderr.write(
            f"ERROR: env var {USER_AGENT_ENV} is required.\n"
            f"  Format: '<your-name> <your-email>'\n"
            f"  Example: export {USER_AGENT_ENV}=\"Kazuya Hibara kazuya@example.com\"\n"
            f"  Why: SEC EDGAR rate-limits anonymous requests and may block UA-less clients.\n"
        )
        sys.exit(1)
    return ua


def resolve_cik(ticker: str, user_agent: str) -> str:
    """Ticker → 10-digit zero-padded CIK.

    TODO: implement
    1. GET https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=<ticker>&type=10-K
       with User-Agent header
    2. parse response (HTML or JSON depending on Accept header)
    3. extract CIK, zero-pad to 10 digits
    4. return as string
    """
    raise NotImplementedError("resolve_cik: stub")


def fetch_filings(
    cik: str,
    form_types: list[str],
    depth: str,
    user_agent: str,
) -> list[dict]:
    """指定 form types の filing list を取得.

    Args:
        cik: 10-digit zero-padded CIK
        form_types: ['10-K', '10-Q', '8-K', 'DEF 14A']
        depth: 'quick' = 各 type 1 件 / 'deep' = 各 type 直近 4 件

    Returns:
        list of {form_type, filing_date, accession_number, primary_document_url, ...}

    TODO: implement
    1. GET {EDGAR_BASE}/submissions/CIK{cik}.json with User-Agent
    2. parse recent.filings (form, filingDate, accessionNumber, primaryDocument)
    3. filter by form_types
    4. limit by depth (quick=1, deep=4)
    5. construct primary_document_url:
       https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_no_dashes}/{primary_document}
    6. return list of dicts
    """
    raise NotImplementedError("fetch_filings: stub")


def download_documents(
    filings: list[dict],
    output_dir: str,
    user_agent: str,
) -> list[str]:
    """filing list を並列 download.

    Returns: list of local file paths.

    TODO: implement
    1. mkdir -p output_dir
    2. for each filing, download primary_document_url to {output_dir}/{filing_date}-{form_type}.{ext}
    3. throttle to RATE_LIMIT_PER_SEC
    4. retry with exponential backoff on 429 / 5xx
    """
    raise NotImplementedError("download_documents: stub")


def main() -> int:
    parser = argparse.ArgumentParser(description="SEC EDGAR filings fetcher")
    parser.add_argument("--ticker", help="Ticker symbol (e.g., AAPL)")
    parser.add_argument("--cik", help="10-digit CIK (skip ticker resolution)")
    parser.add_argument(
        "--types",
        default="10-K,10-Q",
        help="Comma-separated form types (default: 10-K,10-Q)",
    )
    parser.add_argument(
        "--depth",
        choices=("quick", "deep"),
        default="quick",
        help="quick=latest 1 per type / deep=latest 4 per type",
    )
    parser.add_argument(
        "--output-dir",
        default="./downloads",
        help="Local download directory (default: ./downloads)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Pre-flight check (env vars, network) only, no fetch",
    )
    args = parser.parse_args()

    user_agent = check_user_agent()

    if args.check:
        print(f"OK: {USER_AGENT_ENV}={user_agent}")
        # TODO: optional connectivity check (HEAD https://data.sec.gov/)
        return 0

    if not (args.ticker or args.cik):
        parser.error("either --ticker or --cik is required")

    cik = args.cik or resolve_cik(args.ticker, user_agent)
    form_types = [t.strip() for t in args.types.split(",") if t.strip()]
    filings = fetch_filings(cik, form_types, args.depth, user_agent)
    paths = download_documents(filings, args.output_dir, user_agent)

    for p in paths:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
