---
name: ir-source-discovery
description: 米国(SEC EDGAR)・日本(TDnet primary + Firecrawl fallback、EDINET opt-in) のIR資料 URL を発見する agent。Ticker / 証券コード / 会社名から最新の 10-K/10-Q/有報/決算短信 を特定し、JSON manifest を返す。
allowed-tools: Bash, WebFetch, Read, Write
---

# IR Source Discovery Agent

Ticker または証券コードから、上場企業のIR資料 URL を特定する。米国は SEC EDGAR、日本は **TDnet (yanoshin webapi 経由)** を primary、会社 IR サイトの Firecrawl scrape を fallback。EDINET は API key 必要なため opt-in。

## Routing Logic

入力を見て対象市場を判定する:

| 入力パターン | 判定 | 取得経路 |
|---|---|---|
| `^[A-Z]{1,5}$` | US 上場 | SEC EDGAR Submissions API |
| `^\d{4}$` | JP 上場 | TDnet (default、no auth) → 失敗時 Firecrawl fallback → opt-in EDINET |
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

## JP Path: TDnet (Default, no auth)

API key 不要。`scripts/tdnet_fetch.py` (yanoshin webapi 経由) で適時開示を fetch。

```bash
.venv/bin/python scripts/tdnet_fetch.py --code <code> --types kessan-tanshin,setsumei --depth quick --output-dir ./downloads/<code>
```

`--types` の選択肢:
- `kessan-tanshin` (決算短信) — 四半期 / 通期の単体 PDF
- `setsumei` (決算説明資料) — IR プレゼン PDF
- `rinji` (適時開示) — 自己株、株主優待、配当変更等
- `yuho` / `shihanki` (有報・四半期報告書) — TDnet にも一部出るが EDINET の方が網羅的
- `all` — 任意の最新開示

⚠️ **TDnet retention 制約**: PDF は概ね 30 日で release.tdnet.info から削除される。直近の決算開示が無い時期 (四半期と四半期の間) は空配列が返ることがあるので、その時は **JP Fallback (Firecrawl)** に降りる。

## JP Fallback: 会社 IR サイト直 DL (Firecrawl)

TDnet で対象が見つからない (retention 切れ / 古い開示) ときの fallback。`firecrawl` skill で JS render → markdown 抽出 → PDF URL 抽出。

### Step 1: 会社名解決

証券コード (4 桁) から会社名と corporate domain を解決:

```bash
firecrawl scrape "https://finance.yahoo.co.jp/quote/<code>.T" --format markdown --only-main-content
```

### Step 2: IR ページ scrape

会社 IR サイトの「決算発表」「IR ライブラリ」相当ページを Firecrawl で scrape:

```bash
firecrawl scrape "https://www.<corporate-domain>/ir/library/results/" --format markdown --only-main-content
```

よくある IR ページ patterns:

| Pattern | 例 |
|---|---|
| `/ir/library/results/` | サイバーエージェント, リクルート 等 |
| `/ir/financial/` | 任天堂 等 |
| `/ja/ir/library/` | グローバル展開している大手 |
| `/ja/investors/` / `/jp/investors/` | 国際企業 |
| `https://ssl4.eir-parts.net/doc/<code>/ir_material/` | EIR 利用社 |

URL pattern 不明時は Firecrawl search で discovery:

```bash
firecrawl search "<company> 決算短信 IR site:<corporate-domain>"
```

### Step 3: PDF URL 抽出

scrape 結果 (markdown) から PDF URL を抽出。LLM reasoning で「最新の決算短信 / 決算説明会資料 / 有価証券報告書」を識別。

`--depth quick` → 最新の 決算短信 + 決算説明会資料 (2 docs)
`--depth deep` → 直近 4 四半期分 (8 docs まで)

### Step 4: Output manifest

`./manifests/<ticker>-<timestamp>.json` に書き出し (詳細 schema は下記)。

## JP Opt-in: EDINET (`--source edinet` or `EDINET_API_KEY` set)

歴史的な有価証券報告書 / 半期報告書まで網羅したい時に opt-in。要 EDINET API key (https://disclosure2.edinet-fsa.go.jp 経由で無料申請、~1 営業日)。

```bash
.venv/bin/python scripts/edinet_fetch.py --code <code> --types yuho,shihanki --depth deep --output-dir ./downloads/<code>
```

対象 docTypeCode: `120` (有価証券報告書), `140` (四半期報告書), `160` (半期報告書)。`EDINET_API_KEY` env var 未設定時はこのパスを skip。

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
- **TDnet (default JP)**: 公式 API なし、yanoshin webapi (https://webapi.yanoshin.jp/) を 3rd-party wrapper として使用。直近 ~30 日のみ retention、それ以前の PDF は release.tdnet.info から消える。release.tdnet.info は default UA を 403 で弾くため browser-like header 必須 (script で対応済)
- **会社 IR サイト直 scrape (fallback)**: per-company で構造が異なる。`firecrawl` skill 必須 (JS render が要る)。site 改修で URL pattern が breaking change することあり、半年に一度は spot-check
- **EDINET (opt-in)**: API key 必須、無料申請 ~1 営業日。`EDINET_API_KEY` env var 未設定時はこの path 自体を skip
- **会社名 lookup**: 完全一致しない時は ambiguity 判定して user に確認求める (例: "Toyota" → TOYOTA MOTOR / Toyota Industries / Toyota Boshoku)

## Error Handling

- CIK / 銘柄コードが見つからない → exit 1 + suggest user に正しい ticker を依頼
- API rate limit hit → exponential backoff 30s, 60s, 120s で 3 回 retry
- 全パス失敗 → manifest を空配列で出力、errors[] に理由を記録
