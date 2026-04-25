---
name: ir-podcast
description: 上場企業のIR資料 (10-K/10-Q/有報/決算短信) をNotebookLM Audio Overview で podcast 化する end-to-end orchestrator。/ir-podcast <ticker> で単発、/ir-podcast-batch で並列実行。米国(SEC EDGAR)・日本(EDINET) 両対応。
---

# IR Podcast Orchestrator

ビジネス勉強用に上場企業のIR資料を集めて NotebookLM の Audio Overview (podcast) に変換する。歩きながら / 通勤中に passive listening で吸収するための pipeline。

## いつ発火するか

- ユーザーが `/ir-podcast <ticker>` を実行した時
- 「Apple のIRをpodcast化して」「7203 (トヨタ) の決算を音声で」等の自然言語依頼
- `/ir-podcast-batch AAPL,7203,MSFT` で複数銘柄並列処理

## Flow (Orchestrator が順に発火)

### Step 1: Company Resolution
入力 (ticker / 証券コード / 会社名) を canonical identifier に解決。

| 入力パターン | 判定 | 解決先 |
|---|---|---|
| `^[A-Z]{1,5}$` (例: AAPL, MSFT) | US 上場 | SEC EDGAR CIK lookup |
| `^\d{4}$` (例: 7203, 6758) | JP 上場 | EDINET 銘柄コード |
| 会社名 (英/日) | name lookup | WebFetch + ticker lookup |

### Step 2: Source Discovery
`ir-source-discovery` agent を spawn して IR doc URL list を取得。

```
Agent({
  description: "Find latest IR docs for <ticker>",
  subagent_type: "ir-source-discovery",
  prompt: "Discover the latest IR materials for <ticker>. Output JSON manifest of {type, date, url, language}."
})
```

### Step 3: Document Download
取得した URL list から実 file を download。

- US: `python scripts/edgar_fetch.py --cik <CIK> --types 10-K,10-Q,8-K --depth <quick|deep>` (EDGAR API 経由、`EDGAR_USER_AGENT` のみ必要)
- JP (default): `python scripts/ir_site_fetch.py --manifest ./manifests/<ticker>-<ts>.json --output-dir ./downloads/` (会社 IR サイト直 DL、API key 不要)
- JP (optional fallback): `python scripts/edinet_fetch.py --code <4-digit> --types yuho,kessan-tanshin --depth <quick|deep>` ⇒ `EDINET_API_KEY` env var が **set されている時のみ** activate

JP は ir-source-discovery agent が manifest JSON を吐くので、`ir_site_fetch.py` は manifest を消費して PDF を全件 DL する薄い wrapper。

Output: `./downloads/<ticker>/<date>-<type>.{pdf,html}`

### Step 4: Document Analysis (token efficiency)
`ir-document-analyzer` agent を spawn して各 doc から要点抽出 + NotebookLM upload 用最適化。

NotebookLM source 上限 = 200MB / source、500K words / source。大型 PDF は事前に章立て分割推奨。

### Step 5: NotebookLM Notebook Creation
```bash
NOTEBOOK_ID=$(notebooklm create -t "<ticker> IR <date>" --json | jq -r .id)
for f in ./downloads/<ticker>/*.{pdf,md}; do
  notebooklm source add -n $NOTEBOOK_ID -f "$f"
done
notebooklm source wait -n $NOTEBOOK_ID
```

### Step 6: Audio Overview Generation
```bash
notebooklm generate audio -n $NOTEBOOK_ID --lang <ja|en>
notebooklm artifact wait -n $NOTEBOOK_ID --type audio
```

`--lang` default は ticker から判定 (US → en, JP → ja)。`/ir-podcast AAPL --lang ja` で英文資料を日本語ナレーションに変換可能。

### Step 7: Download
```bash
mkdir -p ~/Downloads/ir-podcasts
notebooklm download -n $NOTEBOOK_ID --type audio -o ~/Downloads/ir-podcasts/<ticker>-<date>.wav
```

### Step 8: Notify
完了通知 (macOS):
```bash
terminal-notifier -title "IR Podcast Ready" -message "<ticker> <date> (<duration>min)" -sound default
```

## Pre-flight Checks

実行前に以下を確認 (失敗時は早期 exit + 修復手順案内):

1. `notebooklm auth check --test` — cookie auth が live か (失効してたら `notebooklm login` 案内)
2. US 利用時: `python scripts/edgar_fetch.py --check` — `EDGAR_USER_AGENT` env var 設定済みか
3. JP 利用時: `firecrawl --version` — Firecrawl CLI が install 済みか (会社 IR サイト直 DL に必須)
4. JP optional: `python scripts/edinet_fetch.py --check` — `EDINET_API_KEY` 未設定なら skip (default 経路では不要)

## Output

- Audio: `~/Downloads/ir-podcasts/<ticker>-<YYYYMMDD>.wav`
- Notebook URL: stdout に表示 (NotebookLM web UI でも閲覧可)
- Source docs cache: `./downloads/<ticker>/` (再実行時の cache hit に利用)

## Constraints

- **NotebookLM cookie auth** は不安定 (上流 memo に警告あり)。失効したら `notebooklm login` で再認証
- **SEC EDGAR rate limit**: 10 req/sec。`EDGAR_USER_AGENT` env var 必須 (`<your-name> <your-email>` 形式)
- **JP 直 DL**: `firecrawl` CLI が必要 (会社 IR サイトは大半が JS-rendered)。会社 IR ページの URL pattern は per-company で異なるので agent の reasoning に依存
- **EDINET API key (optional)**: JP の fallback として使う場合のみ必要。利用申請は https://disclosure2.edinet-fsa.go.jp で数営業日。default 経路では不要
- **NotebookLM source 上限**: 50 sources / notebook、各 200MB / 500K words 上限
- **並列実行**: `--parallel N` で N=3 まで推奨 (NotebookLM 側の rate limit 配慮)

## Related Skills

- `firecrawl` (推奨 install) — fallback discovery で利用
- `defuddle` (推奨 install) — HTML → markdown cleanup で token efficiency
- `notebooklm` (依存) — pip 経由で install (`pip install notebooklm-py>=0.3.4`)
