---
description: 単一 ticker の IR資料を取得して NotebookLM podcast 化する on-demand command
---

# /ir-podcast <ticker> [options]

単一の上場企業のIR資料を取得し、NotebookLM Audio Overview で podcast に変換する。

## Usage

```
/ir-podcast <ticker> [--lang ja|en] [--depth quick|deep] [--no-cache]
```

## Arguments

### `<ticker>` (必須)
- US: 1-5 文字 (例: `AAPL`, `MSFT`, `GOOGL`)
- JP: 4 桁証券コード (例: `7203` トヨタ, `6758` ソニー)
- 会社名でも可 (例: `Apple`, `トヨタ自動車`) — 内部で ticker resolution

## Options

### `--lang ja|en` (default: ticker から自動判定)
NotebookLM Audio Overview の音声言語。
- US ticker → `en` (default)
- JP ticker → `ja` (default)
- 英文資料を日本語ナレーションで聞きたい時: `/ir-podcast AAPL --lang ja`

### `--depth quick|deep` (default: `quick`)
- `quick`: 各 form type の最新 1 件 (10-K + 10-Q 直近 = 2 docs)
- `deep`: 過去 4 四半期分 (10-K + 10-Q × 3 = 4 docs、内容厚いが audio が長くなる)

### `--no-cache`
`./downloads/<ticker>/` の cache を無視して再 download

## Examples

```
# 米国: Apple の最新 IR を英語 podcast に
/ir-podcast AAPL

# 日本: トヨタの最新 IR を日本語 podcast に
/ir-podcast 7203

# 英文 IR を日本語ナレーションで
/ir-podcast NVDA --lang ja

# 過去 1 年分の Microsoft IR を深掘り podcast に
/ir-podcast MSFT --depth deep
```

## Flow

`ir-podcast` skill が発火し、以下を順次実行:

1. Company Resolution (ticker → CIK or 証券コード)
2. `ir-source-discovery` agent → IR doc URL list (manifest JSON)
3. Document download:
   - US: `scripts/edgar_fetch.py` (EDGAR API、`EDGAR_USER_AGENT` のみ必要)
   - JP (primary): `scripts/tdnet_fetch.py` (TDnet 適時開示、no auth、~30 日 retention)
   - JP (fallback): `scripts/ir_site_fetch.py` (TDnet 空時、Firecrawl で会社 IR サイト直 DL)
   - JP (opt-in): `scripts/edinet_fetch.py` (`EDINET_API_KEY` set 時のみ、歴史的有報用)
4. `ir-document-analyzer` agent → 章立て抽出 + サイズ最適化
5. `notebooklm create` + `source add` → NotebookLM upload
6. `notebooklm generate audio --lang <lang>` → Audio Overview 生成
7. `notebooklm download` → `~/Downloads/ir-podcasts/<ticker>-<date>.wav` 保存
8. `terminal-notifier` で完了通知

## Output

- Audio: `~/Downloads/ir-podcasts/<ticker>-<YYYYMMDD>.wav`
- Notebook URL: stdout (NotebookLM web UI でも閲覧可能)
- Source cache: `./downloads/<ticker>/` (再実行時 hit)

## Pre-flight Required

初回実行前に以下完了が必要:
1. `pip install -r requirements.txt && playwright install chromium`
2. `notebooklm login` (Google アカウント認証)
3. `export EDGAR_USER_AGENT="<name> <email>"` (US 利用時)
4. JP primary 経路 (TDnet) は追加 setup 不要。fallback で会社 IR サイト直 DL を使う場合は `firecrawl --version` で CLI 確認
5. `export EDINET_API_KEY="<key>"` — **optional**。歴史的有報まで欲しい時のみ。primary/fallback 経路では不要

詳細: `docs/INSTALL.md` + `docs/AUTH.md`

## Schedule (User-side)

`/ir-podcast` は on-demand command。定期実行は user 側で setup:
- macOS launchd / cron
- GitHub Actions weekly workflow

詳細例: `docs/SCHEDULE.md`

## Related

- `/ir-podcast-batch` — 複数 ticker 並列処理
- `/ir-research` — podcast 生成スキップ、テキストサマリのみ
