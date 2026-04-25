"""SEC EDGAR API client (stub).

実装 TODO. 後続セッションで /autopilot 委譲予定。

公式 docs:
- https://www.sec.gov/edgar/sec-api-documentation
- https://www.sec.gov/os/accessing-edgar-data
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx


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
    """Ticker → 10-digit zero-padded CIK."""
    url = "https://www.sec.gov/files/company_tickers.json"
    resp = httpx.get(url, headers={"User-Agent": user_agent}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry["ticker"].upper() == ticker_upper:
            return str(entry["cik_str"]).zfill(10)
    raise ValueError(f"Ticker {ticker} not found in SEC EDGAR")


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
    """
    url = f"{EDGAR_BASE}/submissions/CIK{cik}.json"
    resp = httpx.get(url, headers={"User-Agent": user_agent}, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    recent = data["filings"]["recent"]
    accessions = recent["accessionNumber"]
    dates = recent["filingDate"]
    forms = recent["form"]
    primary_docs = recent["primaryDocument"]

    limit = 1 if depth == "quick" else 4
    counts: dict[str, int] = {}
    results: list[dict] = []

    cik_int = int(cik)
    for accession, date, form, primary_doc in zip(accessions, dates, forms, primary_docs):
        if form not in form_types:
            continue
        if counts.get(form, 0) >= limit:
            continue
        accession_no_dashes = accession.replace("-", "")
        primary_document_url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik_int}"
            f"/{accession_no_dashes}/{primary_doc}"
        )
        results.append({
            "accession_number": accession,
            "filing_date": date,
            "form_type": form,
            "primary_document_url": primary_document_url,
            "primary_document": primary_doc,
        })
        counts[form] = counts.get(form, 0) + 1

    return results


def download_documents(
    filings: list[dict],
    output_dir: str,
    user_agent: str,
) -> list[str]:
    """filing list を download.

    Returns: list of local file paths.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    for filing in filings:
        url = filing["primary_document_url"]
        primary_doc = filing["primary_document"]
        ext = Path(primary_doc).suffix or ".html"
        form_type_safe = filing["form_type"].replace(" ", "_")
        filename = f"{filing['filing_date']}-{form_type_safe}{ext}"
        dest = out / filename

        success = False
        for attempt in range(3):
            time.sleep(1 / RATE_LIMIT_PER_SEC)
            try:
                resp = httpx.get(url, headers={"User-Agent": user_agent}, timeout=60, follow_redirects=True)
                if resp.status_code == 200:
                    dest.write_bytes(resp.content)
                    paths.append(str(dest.resolve()))
                    success = True
                    break
                elif resp.status_code == 429 or resp.status_code >= 500:
                    time.sleep(2 ** (attempt + 1))
                else:
                    sys.stderr.write(f"WARN: skipping {url} (HTTP {resp.status_code})\n")
                    break
            except httpx.RequestError as exc:
                sys.stderr.write(f"WARN: request error for {url}: {exc}\n")
                break

        if not success and resp.status_code not in (200,) and resp.status_code not in range(400, 500):
            sys.stderr.write(f"WARN: failed to download {url} after 3 attempts\n")

    return paths


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
