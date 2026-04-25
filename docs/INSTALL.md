# Installation Guide

ir-podcast-plugin の install と初回 setup 手順。

## 前提

- macOS / Linux (Windows は未検証)
- Python 3.10+
- Claude Code または Codex CLI / Codex desktop インストール済み
- Google アカウント (NotebookLM 利用に必要)

## Step 1: Plugin install

### Codex

Codex CLI で marketplace を追加:

```bash
codex plugin marketplace add Kazuya-Hibara/ir-podcast-plugin
```

追加後、Codex の Plugins 画面で `IR Podcast` を install/enable する。

CLI 設定で直接有効化する場合は `~/.codex/config.toml` に追加:

```toml
[plugins."ir-podcast-plugin@ir-podcast"]
enabled = true
```

### Claude Code

Claude Code 内で marketplace を追加し、plugin を install:

```
/plugin marketplace add https://github.com/Kazuya-Hibara/ir-podcast-plugin
/plugin install ir-podcast-plugin
```

install 完了後、Claude Code を一度 restart して plugin を認識させる。

## Step 2: Python 依存 install

repo 内で:

```bash
cd /path/to/ir-podcast-plugin
pip install -r requirements.txt
playwright install chromium
```

`pip install` が PEP 668 で拒否される (macOS Python 3.12+ 等) 場合は venv 経由:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

ただし plugin 内 venv は config が複雑になるので、**`pipx install notebooklm-py[browser]`** で system-wide install する方が運用が楽 (詳細は `~/.claude/rules/python-venv.md` 参照)。

## Step 3: NotebookLM 認証

```bash
notebooklm login
```

ブラウザが開くので Google アカウントで NotebookLM にログイン。Cookie が `~/.notebooklm/storage_state.json` に保存される。

確認:
```bash
notebooklm auth check --test
# → authenticated: true
```

詳細: [AUTH.md](AUTH.md)

## Step 4: API key 設定

### SEC EDGAR (米国 IR)

User-Agent 必須 (公式ポリシー):

```bash
# ~/.zshrc or ~/.bashrc
export EDGAR_USER_AGENT="<your-name> <your-email>"
```

例: `export EDGAR_USER_AGENT="Kazuya Hibara kazuya@example.com"`

### EDINET (日本 IR)

無料 API key を https://disclosure2.edinet-fsa.go.jp の利用申請から取得。

```bash
export EDINET_API_KEY="<your-key>"
```

US だけ使う場合は EDINET_API_KEY 不要。

## Step 5: 動作確認

```
/ir-podcast-plugin --help    # plugin が listed されることを確認
/ir-research AAPL             # 軽い動作確認 (notebooklm 認証不要)
```

`/ir-research` が成功すれば EDGAR 経路は OK。次に:

```
/ir-podcast AAPL --depth quick
```

5-10 分待つと `~/Downloads/ir-podcasts/AAPL-<date>.wav` が生成される。

## Troubleshooting

| 症状 | 原因 / 対処 |
|---|---|
| `notebooklm: command not found` | `pip install notebooklm-py` が完了していない / PATH に site-packages bin が無い |
| `notebooklm auth check` で `unauthenticated` | `notebooklm login` を再実行 (cookie 失効) |
| `EDGAR_USER_AGENT is required` | `export EDGAR_USER_AGENT="..."` を `.zshrc` に追加して shell 再起動 |
| `EDINET_API_KEY is required` | https://disclosure2.edinet-fsa.go.jp で利用申請 |
| `playwright install` で permission error | sudo 不要、user 権限で再実行 |
| Plugin が `claude plugin list` に出ない | Claude Code を完全に restart (Cmd+Q → 再起動) |

## Uninstall

```
/plugin uninstall ir-podcast-plugin
/plugin marketplace remove ir-podcast
```

`~/.notebooklm/` cookie と env vars は手動削除。
