---
description: IR資料を取得して構造化サマリ markdown を生成 (podcast 化スキップ)
---

# /ir-research <ticker> [options]

`/ir-podcast` の Step 1-4 までを実行し、NotebookLM upload と audio 生成 (Step 5-8) はスキップ。Markdown 形式の構造化サマリを `./reports/<ticker>-<date>.md` に出力する。

## Usage

```
/ir-research <ticker> [--depth quick|deep] [--no-cache]
```

## Arguments / Options

`/ir-podcast` と同じ。`--lang` のみ存在しない (audio 生成しないため)。

## Examples

```
# Apple の構造化サマリ
/ir-research AAPL

# トヨタの過去 4 四半期分を厚めに
/ir-research 7203 --depth deep

# 競合比較 (sequential 実行で diff 取りやすく)
/ir-research AAPL && /ir-research MSFT && /ir-research GOOGL
```

## Use Cases

| シーン | 使い方 |
|---|---|
| **Quick due diligence** | 投資検討前に 30 秒で概要把握 |
| **競合比較** | 同業他社の数値を並べて diff 取る |
| **Watchlist 巡回** | cron で定期生成、変化のあった社だけ podcast 化 |
| **Podcast 前のプレビュー** | 内容確認してから `/ir-podcast` で audio 化 |

## Output

`./reports/<ticker>-<YYYYMMDD>.md`:

- 概要 (報告期間 / 提出日 / ファイリング種別)
- 主要数値 (売上 / 営業利益 / EPS の YoY)
- ガイダンス
- セグメント別内訳
- リスクファクター Top 5
- 役員 / Officers
- 出典 URL list

詳細フォーマットは `agents/ir-document-analyzer.md` 参照。

## Differences from /ir-podcast

| | /ir-podcast | /ir-research |
|---|---|---|
| Step 1-4 (resolve / discover / fetch / analyze) | ✓ | ✓ |
| Step 5 (NotebookLM upload) | ✓ | ✗ |
| Step 6 (Audio generate) | ✓ | ✗ |
| Step 7 (download .wav) | ✓ | ✗ |
| Output | `.wav` (音声) | `.md` (テキスト) |
| 所要時間 | 5-10 min | 1-3 min |
| NotebookLM 認証 | 必須 | 不要 |

`notebooklm login` が未実行でも `/ir-research` は使える。

## Related

- `/ir-podcast <ticker>` — audio 化 full pipeline
- `/ir-podcast-batch` — 複数社 podcast 化
- `agents/ir-document-analyzer.md` — サマリフォーマット詳細
