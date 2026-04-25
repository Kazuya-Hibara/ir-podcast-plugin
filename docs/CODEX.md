# Codex Plugin 対応

この repo は Claude Code plugin と Codex plugin の両方で使える。Codex 側で必要なのは `.agents/plugins/marketplace.json`、`.codex-plugin/plugin.json`、`skills/` で、既存の `scripts/` はそのまま共通利用する。

## 追加したもの

- `.codex-plugin/plugin.json`
  - Codex plugin manifest
  - `skills: "./skills/"` で `ir-podcast` / `ir-research` skill を公開
  - Codex UI 用の `interface` metadata と starter prompt を定義
- `.agents/plugins/marketplace.json`
  - `codex plugin marketplace add Kazuya-Hibara/ir-podcast-plugin` で読まれる marketplace 定義
  - repo root 自体を plugin root として参照する

## Claude 版との違い

| 機能 | Claude Code plugin | Codex plugin |
|---|---|---|
| Manifest | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` |
| Skill | `skills/*/SKILL.md` | `skills/*/SKILL.md` |
| Slash command | `commands/*.md` | そのままは使わない |
| Custom agent | `agents/*.md` | そのままは自動登録されない |
| 実処理 | `scripts/*.py` | 同じ scripts を使う |

Codex で同じ挙動にするには、slash command ではなく自然言語または明示的な skill 指定で起動する。

例:

```text
AAPLの最新IRをpodcast化して。ir-podcast skillを使って。
```

```text
7203のIR資料を取得して、音声化せずに構造化サマリだけ作って。ir-research skillを使って。
```

## インストール方法

GitHub marketplace として追加:

```bash
codex plugin marketplace add Kazuya-Hibara/ir-podcast-plugin
```

追加後、Codex の Plugins 画面で `IR Podcast` を install/enable する。

CLI 設定で直接有効化する場合:

```toml
[plugins."ir-podcast-plugin@ir-podcast"]
enabled = true
```

ローカル checkout から marketplace を追加する場合:

```bash
codex plugin marketplace add /path/to/ir-podcast-plugin
```

この repo の `.agents/plugins/marketplace.json` は次の形になっている:

```json
{
  "name": "ir-podcast",
  "interface": {
    "displayName": "IR Podcast"
  },
  "plugins": [
    {
      "name": "ir-podcast-plugin",
      "source": {
        "source": "local",
        "path": "."
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

`path: "."` にしているのは、この repository の root がそのまま plugin root (`.codex-plugin/`, `skills/`, `scripts/` を含む場所) だから。

## 依存セットアップ

Codex 側でも実行環境の依存は同じ。

```bash
pip install -r requirements.txt
playwright install chromium
notebooklm login
```

環境変数:

```bash
export EDGAR_USER_AGENT="Your Name your@email.com"
export EDINET_API_KEY="your-key"
```

## 同じ挙動に近づける実装方針

### 1. Skill を Codex の入口にする

Codex は `.codex-plugin/plugin.json` の `skills` から `SKILL.md` を読み込める。既存の `ir-podcast` / `ir-research` skill をそのまま入口にする。

### 2. Slash command は prompt または script に寄せる

Codex plugin manifest には Claude の `commands/*.md` 相当の entry point がないため、`/ir-podcast AAPL` と完全同形にはしない。代わりに次のどちらかに寄せる。

- Codex への自然言語依頼: `AAPLの最新IRをpodcast化して`
- shell からの deterministic CLI: `python scripts/...`

将来 `/ir-podcast` と同じ体験を強めるなら、`scripts/ir_podcast_cli.py` のような薄い CLI を追加し、skill からその CLI を呼ぶ形が扱いやすい。

### 3. Custom agent は skill 内の手順として読む

Claude の `agents/ir-source-discovery.md` と `agents/ir-document-analyzer.md` は、Codex では custom subagent として自動登録されない。Codex で再現する場合は、skill が必要に応じてこれらの markdown を参照し、同じ役割を Codex 本体または通常の sub-agent delegation で実行する。

### 4. I/O は scripts に閉じ込める

SEC EDGAR / EDINET / NotebookLM の処理は `scripts/*.py` に寄せる。これは Codex でも Claude でも同じで、plugin runtime の違いに左右されにくい。

## 現時点の注意

README のロードマップどおり、Python script 本体にはまだ stub が含まれる。Codex manifest を追加しても、実 podcast 生成の完成度は `scripts/edgar_fetch.py` / `scripts/edinet_fetch.py` / `scripts/nbl_pipeline.py` の実装状況に依存する。
