---
name: ir-research
description: IR資料を取得して構造化サマリだけ生成する (podcast 生成スキップ)。Quick due diligence や複数社比較に。/ir-research <ticker> で発火。
---

# IR Research (Audio Skip)

`ir-podcast` の Step 1-4 までを実行し、Step 5-8 (NotebookLM upload + audio 生成) はスキップ。Markdown 形式の構造化サマリを `./reports/<ticker>-<date>.md` に出力する。

## いつ発火するか

- `/ir-research <ticker>` 実行時
- 「Apple の最新IR内容を要約して」「7203の決算ハイライトだけ知りたい」等
- 複数社比較 (`/ir-research AAPL && /ir-research MSFT && /ir-research GOOGL`)
- Audio が不要・テキストで読みたい場合

## Flow

`ir-podcast` skill の Step 1-4 と同じ:

1. Company Resolution
2. `ir-source-discovery` agent 発火 → IR doc URL list
3. Document Download (`scripts/edgar_fetch.py` or `edinet_fetch.py`)
4. `ir-document-analyzer` agent 発火 → 構造化サマリ生成

## Output

`./reports/<ticker>-<YYYYMMDD>.md`:

```markdown
# <Company> IR Summary - <Date>

## 概要
- ティッカー / 証券コード
- 業種 / セクター
- 直近決算期

## 主要数値 (YoY)
- 売上高
- 営業利益 / EPS
- ガイダンス

## セグメント別内訳
- ...

## リスクファクター (Top 5)
- ...

## 役員 / Officers
- ...

## 出典
- 10-K (URL)
- 10-Q (URL)
- 決算短信 (URL)
```

## Use Cases

- **Due diligence**: 投資検討前の素早い概要把握
- **競合比較**: 同業他社を `/ir-research` で並べて diff
- **Watchlist 巡回**: cron 経由で定期生成 (`SCHEDULE.md` 参照)
- **Podcast 化前のプレビュー**: 内容確認してから `/ir-podcast` で audio 化

## Related

- `/ir-podcast <ticker>` — audio 化まで含めた full pipeline
- `firecrawl` skill — 公式IRページ scrape の fallback
