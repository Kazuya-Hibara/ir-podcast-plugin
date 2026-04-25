---
description: 複数 ticker のIR資料を並列で取得して NotebookLM podcast 化する batch command
---

# /ir-podcast-batch <ticker1,ticker2,...> [options]

複数の上場企業を並列で podcast 化する。Watchlist 全社を 1 コマンドで処理。

## Usage

```
/ir-podcast-batch <ticker1,ticker2,...> [--parallel N] [--lang ja|en] [--depth quick|deep]
```

## Arguments

### `<tickers>` (必須)
カンマ区切りの ticker / 証券コード / 会社名 list。

```
/ir-podcast-batch AAPL,MSFT,GOOGL
/ir-podcast-batch 7203,6758,9984
/ir-podcast-batch AAPL,7203,Stripe  # 米日混在 OK
```

外部ファイルから読み込む場合:
```
/ir-podcast-batch $(cat examples/companies.yaml | yq '.watchlist[]' | paste -sd,)
```

## Options

### `--parallel N` (default: 3)
並列実行数。
- `N=1`: 完全 sequential (debug 向け)
- `N=3`: 推奨 (NotebookLM 側 rate limit に配慮)
- `N=5`: 上限 (`~/.claude/rules/agent-rate-limit` 準拠)
- `N>5`: 拒否 (rate limit 違反リスク)

### `--lang`, `--depth`, `--no-cache`
`/ir-podcast` と同じ。全 ticker に同じ設定が適用される。混在指定したい場合は個別 `/ir-podcast` を複数発行。

## Examples

```
# 米国 mega-cap 5 社を quick podcast 化
/ir-podcast-batch AAPL,MSFT,GOOGL,AMZN,META

# 日本の watchlist 3 社を deep mode で
/ir-podcast-batch 7203,6758,9984 --depth deep

# 並列 5 で時短
/ir-podcast-batch $(cat companies.txt | tr '\n' ',') --parallel 5
```

## Flow

各 ticker について `/ir-podcast` の Step 1-8 を並列実行。Output ファイルは `~/Downloads/ir-podcasts/<ticker>-<YYYYMMDD>.wav` に個別保存。

並列度 N で 1 ticker の所要時間 (約 5-10 分) を amortize、5 社で約 10-15 分目安。

## Watchlist 連携

`examples/companies.yaml` テンプレート:

```yaml
watchlist:
  us_mega_cap:
    - AAPL
    - MSFT
    - GOOGL
  jp_auto:
    - 7203  # Toyota
    - 7267  # Honda
  jp_tech:
    - 6758  # Sony
    - 9984  # SoftBank
```

User 側 cron で週次実行:
```bash
0 7 * * 1 cd ~/projects/ir-podcast-plugin && \
  claude -p "/ir-podcast-batch $(yq '.watchlist[][]' examples/companies.yaml | paste -sd,)"
```

## Failure Handling

1 社失敗しても他社は続行 (`--parallel` 同士は独立)。失敗 ticker は stderr に list 表示し、log に reason を記録。
完了通知 (`terminal-notifier`) には `5/5 done` or `3/5 done (failed: NVDA, TSLA)` 形式で結果を含める。

## Related

- `/ir-podcast <ticker>` — 単発実行
- `examples/companies.yaml` — watchlist テンプレート
- `docs/SCHEDULE.md` — cron / launchd / GitHub Actions 連携例
