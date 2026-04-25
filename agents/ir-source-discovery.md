---
name: ir-source-discovery
description: 米国(SEC EDGAR)・日本(EDINET) のIR資料 URL を発見する agent。Ticker / 証券コード / 会社名から最新の 10-K/10-Q/有報/決算短信 を特定し、JSON manifest を返す。
allowed-tools: Bash, WebFetch, Read, Write
---

# IR Source Discovery Agent

Ticker または証券コードから、上場企業のIR資料 URL を特定する。米国は SEC EDGAR、日本は EDINET の公式 API を第一手段とし、見つからない場合のみ Firecrawl で各社IRページを scrape する fallback パスを持つ。

## Routing Logic

入力を見て対象市場を判定する:

| 入力パターン | 判定 | 取得経路 |
|---|---|---|
| `^[A-Z]{1,5}$` | US 上場 | SEC EDGAR Submissions API |
| `^\d{4}$` | JP 上場 | EDINET Documents API |
| その他 (会社名) | 名前解決必要 | WebFetch で ticker 検索 → 上記分岐へ |

判定が曖昧な場合 (例: `T` = AT&T か?)、`WebFetch("https://finance.yahoo.com/lookup?s=<input>")` で確認してから進む。

## US Path: SEC EDGAR

1. **CIK 解決**:
   ```bash
   CIK=$(curl -s "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=<ticker>&type=10-K&dateb=&owner=include&count=40" | grep -oE 'CIK=[0-9]+' | head -1 | cut -d= -f2 | xargs printf "%010d")
   ```

2. **Filings 取得** (User-Agent 必須):
   ```bash
   curl -H "User-Agent: $EDGAR_USER_AGENT" "https://data.sec.gov/submissions/CIK${CIK}.json"
   ```

3. **対象 form タイプの最新 N 件抽出**:
   - `10-K` (年次), `10-Q` (四半期), `8-K` (随時開示), `DEF 14A` (株主総会資料)
   - `--depth quick` → 各 type 1 件 / `--depth deep` → 各 type 直近 4 四半期分

4. **Document URL 構築**: EDGAR のアクセス番号から PDF/HTML URL を生成

`EDGAR_USER_AGENT` env var 未設定の場合は exit 1。SEC のポリシー違反になる。

## JP Path: EDINET

1. **EDINET API key 確認**: `EDINET_API_KEY` env var
2. **書類一覧取得**:
   ```bash
   curl "https://disclosure2.edinet-fsa.go.jp/api/v2/documents.json?date=YYYY-MM-DD&type=2&Subscription-Key=$EDINET_API_KEY"
   ```
3. **対象 docTypeCode 抽出**:
   - `120` (有価証券報告書), `140` (四半期報告書), `160` (半期報告書)
   - 別途 TDnet で `決算短信` (適時開示) も取得可
4. **PDF download URL** 構築

## Fallback: Firecrawl

API 経由で見つからない場合のみ:

```
firecrawl search "<company> investor relations annual report site:<corporate-domain>"
firecrawl scrape <ir-page-url> --format markdown
```

`firecrawl` skill が install されていない場合は warn & skip (hard fail はしない)。

## Output Format

`./manifests/<ticker>-<timestamp>.json`:

```json
{
  "ticker": "AAPL",
  "company": "Apple Inc.",
  "market": "US",
  "discovered_at": "2026-04-25T19:30:00Z",
  "sources": [
    {
      "type": "10-K",
      "date": "2025-09-28",
      "language": "en",
      "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20250928.htm",
      "title": "Annual Report (10-K)",
      "size_estimate_kb": 1024,
      "source": "EDGAR"
    },
    {
      "type": "10-Q",
      "date": "2025-12-28",
      "language": "en",
      "url": "...",
      "source": "EDGAR"
    }
  ]
}
```

## Constraints

- **EDGAR**: `User-Agent: <name> <email>` 必須、10 req/sec rate limit
- **EDINET**: API key 必須、商用利用は別途利用規約確認
- **TDnet**: 公式 API なし、scrape は html 構造変更で頻繁に壊れる
- **会社名 lookup**: 完全一致しない時は ambiguity 判定して user に確認求める (例: "Toyota" → TOYOTA MOTOR / Toyota Industries / Toyota Boshoku)

## Error Handling

- CIK / 銘柄コードが見つからない → exit 1 + suggest user に正しい ticker を依頼
- API rate limit hit → exponential backoff 30s, 60s, 120s で 3 回 retry
- 全パス失敗 → manifest を空配列で出力、errors[] に理由を記録
