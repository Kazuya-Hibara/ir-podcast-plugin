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

### Codex plugin として使う場合

Codex 版 manifest は `.codex-plugin/plugin.json` に追加済み。Codex では Claude Code の `commands/*.md` はそのまま slash command としては動かないため、自然言語または skill 指定で起動する。

```text
AAPLの最新IRをpodcast化して。ir-podcast skillを使って。
7203のIR資料を取得して構造化サマリだけ作って。ir-research skillを使って。
```

詳細: [docs/CODEX.md](docs/CODEX.md)

### Claude Code plugin として使う場合

#### 1. Install

Claude Code 内で:

```
/plugin marketplace add Kazuya-Hibara/ir-podcast-plugin
/plugin install ir-podcast-plugin@ir-podcast
```

> ⚠️ Install 後、**Claude Code を一度 restart** (`/exit` → 再起動) すると `/ir-podcast` 等の slash command が `/help` に表示される。
>
> ⚠️ `/plugin marketplace add` + `/plugin install` を **両方** 実行しないと `installed_plugins.json` にエントリが入らず、ターミナル入力での short alias `/ir-podcast` は登録されない (cache だけ作られる "partial install" 状態)。Skill tool 経由 (`ir-podcast-plugin:ir-podcast`) は cache だけでも動くので、project root から起動する Claude Code 内では問題なし。

#### 2. 依存セットアップ

```bash
cd ~/.claude/plugins/cache/ir-podcast/ir-podcast-plugin/0.1.0
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
.venv/bin/notebooklm login   # Google アカウントで NotebookLM 認証 (browser OAuth)
```

#### 3. API キー設定

```bash
# ~/.zshrc に追加
export EDGAR_USER_AGENT="<Your Name> <your@email.com>"   # 必須: SEC fair-use policy
# JP は TDnet 経由で auth 不要。歴史的な有報まで網羅したいときだけ ↓ を opt-in:
# export EDINET_API_KEY="<your-key>"
```

> ⚠️ `EDGAR_USER_AGENT` には **必ず自分の名前と email** を入れる。これは SEC が連絡可能な identifier を要求するポリシーで、他人の email を流用すると レート制限/ban が本人に飛ぶ。
>
> JP の default 経路は **TDnet** (適時開示、no auth)。直近 ~30 日の決算短信 / 決算説明資料 / 適時開示 PDF を取得。古い有報まで欲しい場合のみ EDINET API key を https://disclosure2.edinet-fsa.go.jp で申請 (無料、~1 営業日)。

詳細: [docs/INSTALL.md](docs/INSTALL.md) / [docs/AUTH.md](docs/AUTH.md)

#### 4. 実行

```
/ir-podcast AAPL
```

15-25 分後、`~/Downloads/ir-podcasts/AAPL-<date>.mp3` が生成される (実態は MPEG-4 audio container)。

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
- [x] Python script 本体実装 (`scripts/edgar_fetch.py`, `edinet_fetch.py`, `nbl_pipeline.py`)
- [x] EDGAR live verify (AAPL → CIK 0000320193 → 10-K/10-Q URL 取得)
- [x] TDnet live verify (7203 Toyota → 510 KB PDF、yanoshin webapi + browser-header httpx)
- [ ] EDINET live verify (opt-in、要 API key)
- [x] NotebookLM E2E smoke (AAPL 10-K → 21 MB m4a "Apple's 416 Billion Dollar Empire Under Siege"、生成 ~20 min)

v0.2.0 (予定):
- 前回 podcast との差分検出 (新規開示のみ podcast 化)
- Slack / Discord 通知
- 統合報告書 (Annual Report) の自動分割 (NotebookLM の 200 MB 上限対応)

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
