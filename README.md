# ir-podcast-plugin

> 上場企業のIR資料 (10-K / 10-Q / 有価証券報告書 / 決算短信) を NotebookLM の Audio Overview で **podcast 化** する Claude Code plugin。歩きながら / 通勤中に passive listening でビジネス勉強。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## できること

- `/ir-podcast AAPL` 一発で Apple の最新 IR を audio podcast (.wav) に変換
- **米国 (SEC EDGAR)** と **日本 (EDINET)** の両方に対応、ticker から自動 routing
- `/ir-podcast-batch AAPL,7203,MSFT` で複数銘柄を並列処理
- `/ir-research <ticker>` で podcast スキップ・テキストサマリだけ生成
- Cron / launchd / GitHub Actions と組み合わせて **watchlist 巡回** も可能 (user 側 schedule)

## なぜ作ったか

決算資料 (10-K, 有報) は数百ページで読むのが大変。一方 NotebookLM の Audio Overview は資料を **2 人の話者の対話形式の podcast** に変換してくれる。これを通勤中 / 散歩中に聞ければ、知識吸収の摩擦が一気に下がる。

ただし手動で「IR ページ訪問 → PDF DL → NotebookLM upload → notebook 作成 → audio 生成 → DL」を繰り返すのはダルい。Claude Code plugin として 1 コマンド化する。

## 構成

```
ir-podcast-plugin/
├── .claude-plugin/        # Plugin manifest (plugin.json + marketplace.json)
├── skills/
│   ├── ir-podcast/        # End-to-end orchestrator
│   └── ir-research/       # Audio skip 版
├── agents/
│   ├── ir-source-discovery.md   # US/JP routing + IR doc URL 発見
│   └── ir-document-analyzer.md  # PDF/HTML 整形 + 構造化サマリ
├── commands/              # /ir-podcast, /ir-podcast-batch, /ir-research
├── scripts/               # Python helpers (EDGAR / EDINET API + NotebookLM CLI wrapper)
├── docs/                  # INSTALL / AUTH / SCHEDULE / ARCHITECTURE
└── examples/              # companies.yaml watchlist + GitHub Actions sample
```

詳細: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Quick Start

### 1. Install

Claude Code 内で:

```
/plugin marketplace add https://github.com/Kazuya-Hibara/ir-podcast-plugin
/plugin install ir-podcast-plugin
```

### 2. 依存セットアップ

```bash
cd ~/.claude/plugins/marketplaces/ir-podcast/ir-podcast-plugin
pip install -r requirements.txt
playwright install chromium
notebooklm login   # Google アカウントで NotebookLM 認証
```

### 3. API キー設定

```bash
# ~/.zshrc
export EDGAR_USER_AGENT="Your Name your@email.com"   # SEC EDGAR ポリシー (必須)
export EDINET_API_KEY="your-key"                     # EDINET (JP 利用時のみ)
```

EDINET API key は https://disclosure2.edinet-fsa.go.jp で無料申請。

詳細: [docs/INSTALL.md](docs/INSTALL.md) / [docs/AUTH.md](docs/AUTH.md)

### 4. 実行

```
/ir-podcast AAPL
```

5-10 分後、`~/Downloads/ir-podcasts/AAPL-<date>.wav` が生成される。

## 使用例

```bash
# 米国 mega-cap の最新 IR を一気に
/ir-podcast-batch AAPL,MSFT,GOOGL,AMZN,META

# トヨタの過去 4 四半期分を深掘り
/ir-podcast 7203 --depth deep

# 英文 IR を日本語ナレーションで聞く
/ir-podcast NVDA --lang ja

# 音声不要、テキストサマリだけ
/ir-research 6758
```

## 定期実行

Plugin 自体は cron を内蔵していない (透明性 / 柔軟性のため、user 側で schedule)。

- **macOS launchd** — 常時稼働 Mac 向け
- **cron** — Linux server 向け
- **GitHub Actions** — remote 24/7 実行向け

サンプル設定: [docs/SCHEDULE.md](docs/SCHEDULE.md) / [examples/github-actions.yml](examples/github-actions.yml)

## 依存

| | バージョン | 用途 |
|---|---|---|
| [`notebooklm-py`](https://github.com/teng-lin/notebooklm-py) | `>=0.3.4` | NotebookLM CLI (MIT, ⭐11k+) |
| `httpx` | `>=0.27` | EDGAR / EDINET HTTP client |
| `PyYAML` | `>=6.0` | watchlist parsing |
| `playwright` (auto) | latest | NotebookLM cookie auth |

Optional:
- [`firecrawl`](https://github.com/firecrawl/firecrawl) skill — fallback IR discovery
- [`defuddle`](https://github.com/kepano/defuddle) skill — HTML cleanup

## 制約

- NotebookLM は **non-official** API (Playwright cookie auth)、cookie が時々失効する → `notebooklm login` で都度更新
- SEC EDGAR は `User-Agent` header 必須 (公式ポリシー)
- EDINET は無料だが利用申請が必要
- NotebookLM source 上限 50 件 / notebook、各 200MB
- 1 podcast あたり 5-10 分の生成時間 (深堀 mode は 15-20 分)

## ロードマップ

v0.1.0 (現在):
- [x] Plugin scaffold (skills + agents + commands + manifests)
- [ ] Python script 本体実装 (現在 stub)
- [ ] 動作確認 (実 NotebookLM 認証 + EDGAR / EDINET API)

v0.2.0 (予定):
- TDnet (適時開示) 取得
- 前回 podcast との差分検出 (新規開示のみ podcast 化)
- Slack / Discord 通知

v1.0.0 (将来):
- 韓国 (DART) / 香港 (HKEX) 対応
- 字幕付き video 生成

## Contributing

Issues / PRs 歓迎。特に欲しい contribution:
- 他 region (DART, HKEX, ASX 等) の IR API client
- NotebookLM cookie auth の安定化
- watchlist YAML format の標準化提案

## License

[MIT](LICENSE) — 上流 `notebooklm-py` (MIT) と整合。

## 関連プロジェクト

- [teng-lin/notebooklm-py](https://github.com/teng-lin/notebooklm-py) — 上流 NotebookLM Python CLI (MIT, ⭐11k+)
- [Claude Code](https://claude.com/claude-code) — Plugin が動く環境
