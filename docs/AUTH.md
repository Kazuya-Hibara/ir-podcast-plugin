# Authentication Guide

ir-podcast-plugin が必要とする 3 種類の認証 (NotebookLM cookie / SEC EDGAR User-Agent / EDINET API key) の取得・設定・更新ガイド。

## 1. NotebookLM (cookie auth)

NotebookLM には公式 public API がない。`notebooklm-py` (上流 CLI) は Playwright で browser cookie を取得して private API を叩く。

### 初回セットアップ

```bash
notebooklm login
```

ブラウザ (chromium) が開く → Google アカウントで NotebookLM にログイン → cookie が `~/.notebooklm/storage_state.json` に保存される。

### 動作確認

```bash
notebooklm auth check --test
# → authenticated: true
```

### Cookie 失効時

NotebookLM cookie は時々失効する (上流 memo に "Cookie認証の不安定さ" 警告)。失効すると以下が出る:

```
ERROR: NotebookLM not authenticated. Run: notebooklm login
```

対処: 再 login するだけ。

```bash
notebooklm login
```

### Cookie ファイル削除 (clean reset)

```bash
rm -rf ~/.notebooklm/
notebooklm login
```

### CI/CD で使う場合

CI 環境では browser を立ち上げられないので、ローカルで取得した `storage_state.json` を secret として CI に injection する。GitHub Actions 例:

```yaml
- name: Restore NotebookLM cookie
  run: |
    mkdir -p ~/.notebooklm
    echo '${{ secrets.NOTEBOOKLM_STORAGE_STATE }}' > ~/.notebooklm/storage_state.json
```

`storage_state.json` の中身全体を `NOTEBOOKLM_STORAGE_STATE` secret に登録 (約 5-10KB)。

**注意**: cookie は時々 rotate されるので、CI で動かなくなったら local で再 login → secret 更新。

## 2. SEC EDGAR (User-Agent header)

SEC EDGAR の rate limit ポリシー (https://www.sec.gov/os/accessing-edgar-data) で User-Agent header が必須。違反すると anonymous IP block されることがある。

### Format

```
<your-name> <your-email>
```

例: `Kazuya Hibara kazuya@example.com`

### 設定

```bash
# ~/.zshrc or ~/.bashrc
export EDGAR_USER_AGENT="<your-name> <your-email>"
```

shell 再起動 or `source ~/.zshrc`。

### 確認

```bash
python scripts/edgar_fetch.py --check
# → OK: EDGAR_USER_AGENT=Kazuya Hibara kazuya@example.com
```

### 取得不要

無料・登録不要。env var を設定するだけ。

## 3. EDINET (API key)

EDINET (日本の有報・四半期報告書) の API は **無料だが利用申請が必要**。

### 取得手順

1. https://disclosure2.edinet-fsa.go.jp/weee0010.aspx にアクセス
2. 「API利用申請」を選択
3. 必要事項記入 (氏名 / 連絡先 / 利用目的)
4. 数営業日後、メールで Subscription Key 受領

### 設定

```bash
# ~/.zshrc or ~/.bashrc
export EDINET_API_KEY="<your-subscription-key>"
```

### 確認

```bash
python scripts/edinet_fetch.py --check
# → OK: EDINET_API_KEY=<masked, 32 chars>
```

### Rate limit

EDINET API には rate limit が明示されていないが、過度な並列 request は控える (推奨: 並列 5 以下、間隔 100ms 以上)。

## Security Best Practices

- **Secret は git に commit しない**: `.gitignore` で `.env` 除外済み
- **`storage_state.json` も secret 扱い**: NotebookLM session cookie が含まれる
- **EDGAR_USER_AGENT は本物の email** を使う (SEC が問い合わせる可能性あり、fake mail は規約違反)
- **API key の再生成**: EDINET key が漏洩したら disclosure2 site から再発行

## Auth Status まとめ確認

```bash
# 全 auth を 1 コマンドで確認
notebooklm auth check --test && \
  python scripts/edgar_fetch.py --check && \
  python scripts/edinet_fetch.py --check && \
  echo "All auth OK"
```
