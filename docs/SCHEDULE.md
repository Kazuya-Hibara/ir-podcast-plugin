# Scheduling Guide

ir-podcast-plugin は **on-demand command** として設計されており、内蔵スケジューラを持たない。定期実行は user 側で setup する。本ドキュメントは 3 つの代表的な setup 例 (macOS launchd / cron / GitHub Actions) を示す。

## 設計思想

Plugin に cron を内蔵しなかった理由:
- 透明性: スケジューラは user の environment で動かした方が debug しやすい
- 柔軟性: User の cron / launchd / GitHub Actions / k8s CronJob 等、好きな方式を選べる
- 状態を持たない: Plugin 自体は pure tool として保つ

## 共通: companies.yaml watchlist

`examples/companies.yaml` を参考に自分の watchlist を作成:

```yaml
# ~/.config/ir-podcast/companies.yaml
watchlist:
  us_mega_cap:
    - AAPL
    - MSFT
    - GOOGL
  jp_auto:
    - 7203  # Toyota
    - 7267  # Honda
```

ticker list を抽出:
```bash
yq '.watchlist[][]' ~/.config/ir-podcast/companies.yaml | paste -sd,
# → AAPL,MSFT,GOOGL,7203,7267
```

## Pattern 1: macOS launchd (推奨 for Mac)

毎週月曜 7:00 に watchlist 全社を quick podcast 化。

`~/Library/LaunchAgents/com.user.ir-podcast.weekly.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.user.ir-podcast.weekly</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>cd ~/projects/ir-podcast && claude -p "/ir-podcast-batch $(yq '.watchlist[][]' ~/.config/ir-podcast/companies.yaml | paste -sd,)"</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>1</integer>
    <key>Hour</key><integer>7</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/tmp/ir-podcast.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/ir-podcast.err</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>EDGAR_USER_AGENT</key>
    <string>Your Name your@email.com</string>
    <key>EDINET_API_KEY</key>
    <string>your-key</string>
  </dict>
</dict>
</plist>
```

登録:
```bash
launchctl load ~/Library/LaunchAgents/com.user.ir-podcast.weekly.plist
launchctl list | grep ir-podcast
```

手動実行で動作確認:
```bash
launchctl start com.user.ir-podcast.weekly
tail -f /tmp/ir-podcast.log
```

## Pattern 2: cron (Linux / macOS 共通)

`crontab -e`:

```cron
# 毎週月曜 7:00 に watchlist 全社 podcast 化
0 7 * * 1 cd $HOME/projects/ir-podcast && \
  source $HOME/.zshrc && \
  claude -p "/ir-podcast-batch $(yq '.watchlist[][]' $HOME/.config/ir-podcast/companies.yaml | paste -sd,)" \
  >> /tmp/ir-podcast.log 2>&1
```

**注意**: cron 環境は `.zshrc` を読まないので env var を `source ~/.zshrc` で明示 load するか、crontab に直接 `EDGAR_USER_AGENT="..."` 行を書く。

## Pattern 3: GitHub Actions (CI/CD)

remote 環境で実行したい場合 (例: 自分の Mac が off の時間帯)。

`.github/workflows/weekly-ir-podcast.yml`:

```yaml
name: Weekly IR Podcast Generation

on:
  schedule:
    - cron: '0 22 * * 0'  # 毎週日曜 22:00 UTC = 月曜 7:00 JST
  workflow_dispatch:  # 手動実行も可

jobs:
  generate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        ticker: [AAPL, MSFT, GOOGL, 7203, 7267]
      max-parallel: 3
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Claude Code
        run: npm i -g @anthropic-ai/claude-code

      - name: Install plugin deps
        run: |
          pip install -r requirements.txt
          playwright install chromium --with-deps

      - name: Restore NotebookLM cookie
        run: |
          mkdir -p ~/.notebooklm
          echo '${{ secrets.NOTEBOOKLM_STORAGE_STATE }}' > ~/.notebooklm/storage_state.json

      - name: Generate podcast for ${{ matrix.ticker }}
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          EDGAR_USER_AGENT: ${{ secrets.EDGAR_USER_AGENT }}
          EDINET_API_KEY: ${{ secrets.EDINET_API_KEY }}
        run: |
          claude -p "/ir-podcast ${{ matrix.ticker }} --depth quick"

      - name: Upload audio to S3 / GCS
        # 別 step で生成された .wav を任意の storage に upload
        # ここでは省略
        run: ls -la ~/Downloads/ir-podcasts/
```

完成版は `examples/github-actions.yml` を参照。

### CI 用 secrets 一覧

| Secret name | 用途 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude Code が plugin を実行するため (or OAuth subscription) |
| `EDGAR_USER_AGENT` | SEC EDGAR User-Agent header |
| `EDINET_API_KEY` | EDINET API key (JP 利用時) |
| `NOTEBOOKLM_STORAGE_STATE` | NotebookLM cookie JSON 全体 |

## Pattern 比較

| Pattern | Pros | Cons | 推奨ケース |
|---|---|---|---|
| **launchd** | Mac native、env var 完全 control、debug 容易 | Mac が起きてないと動かない | 個人用 (常時稼働 Mac mini 等) |
| **cron** | UNIX 標準、シンプル | env load の罠 | Linux server / 詳しい人 |
| **GitHub Actions** | remote 実行、Mac off でも OK | secret 設定が手間、cookie rotate 時に手動更新 | チーム共有 / 24/7 実行 |

## 完了通知

各 pattern で完了通知を追加したい場合:

- macOS launchd: `terminal-notifier` 内蔵
- cron: `osascript -e 'display notification ...'` で macOS native
- GitHub Actions: Slack Webhook / Discord Webhook step を追加

## Watchlist 巡回戦略

毎週同じ社で同じ docs を取得しても podcast 内容が同じになる。以下のいずれかの戦略を推奨:

1. **新規開示のみ podcast 化**: `/ir-research` 先行で diff 検出 → 変化あり社のみ `/ir-podcast`
2. **四半期回し**: 1Q/2Q/3Q/4Q のどれかが直近 30 日に出た社のみ
3. **manual cherry-pick**: cron は無効化し、興味ある社を都度 `/ir-podcast`

`/ir-research` の差分判定は別 script で実装可能 (out of scope for v0.1.0)。
