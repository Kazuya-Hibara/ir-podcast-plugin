---
name: ir-document-analyzer
description: IR資料 (PDF/HTML) を NotebookLM upload 向けに最適化 + 構造化サマリ生成する agent。サイズ削減・重複除去・章立て抽出を担当。
allowed-tools: Read, Bash, Write
---

# IR Document Analyzer

`ir-source-discovery` が発見した IR doc を NotebookLM upload に向けて整形する。NotebookLM の source 上限 (200MB / 500K words) を超えないようにファイルサイズ最適化と、`ir-research` skill 用の構造化サマリ生成を担当する。

## 責務

1. **PDF → text 変換** (`pdftotext` via Bash)
2. **HTML → markdown 変換** (`defuddle` skill 委譲、未 install なら fallback で sed/awk)
3. **重複除去**: 10-K と Annual Report、有報と統合報告書は内容重複多い → 章立てで diff 検出
4. **章立て抽出**: 主要セクション (Item 1: Business / Item 1A: Risk Factors / 等) を index 化
5. **構造化サマリ生成**: revenue / YoY / guidance / risks / officers / segment breakdown
6. **サイズ最適化**: 200MB を超える PDF は章単位で分割

## Tools

### PDF → text
```bash
pdftotext -layout -nopgbrk "<input.pdf>" "<output.txt>"
```

`pdftotext` が無い場合: `python3 -c "import pypdf2"` で fallback (slower)

### HTML → markdown
```bash
# Defuddle skill が available の場合
defuddle <url-or-file> --format markdown

# Fallback (powerful tool が無い時)
python3 scripts/html_to_md.py <input.html> > <output.md>
```

### Metadata 抽出
PDF の最初 5 ページから:
- 提出日 / 報告期間
- 会社名 / 証券コード / CIK
- 監査法人

## 構造化サマリ Format

```markdown
# <Company> <Filing Type> - <Period End Date>

## 1. 概要
- 報告期間: YYYY-MM-DD ~ YYYY-MM-DD
- 提出日: YYYY-MM-DD
- ファイリング種別: 10-K / 10-Q / 有報 / 決算短信

## 2. 主要数値 (YoY 比較)

| 指標 | 当期 | 前期 | YoY |
|---|---|---|---|
| 売上高 | $X.XB | $Y.YB | +Z.Z% |
| 営業利益 | ... | ... | ... |
| 純利益 | ... | ... | ... |
| EPS | ... | ... | ... |

## 3. ガイダンス (forward-looking)
- 次期予想売上: $X.XB ~ $Y.YB
- 次期予想 EPS: $A.AA ~ $B.BB
- 主要前提条件:

## 4. セグメント別内訳
| セグメント | 売上 | YoY | 営業利益率 |
|---|---|---|---|

## 5. リスクファクター (Top 5)
1. ...
2. ...

## 6. 役員 / Officers
- CEO:
- CFO:
- (執行役員のうち主要メンバー)

## 7. 監査・ガバナンス note
- 監査法人:
- 株主総会:
- 重要な後発事象:

## 8. NotebookLM Upload 用 cleaned text
[本文へのリンクまたは embed]
```

## Dedup Heuristics

10-K と Annual Report が両方ある場合:
- ファイルサイズ・ページ数を比較
- 章タイトル set の Jaccard 類似度 > 0.8 → 重複と判定
- 大きい方を残す (通常 10-K が法定書式で詳細)

有報と統合報告書:
- 有報は法定 (定型)、統合報告書は任意 (経営戦略含む)
- 両方 keep を default、user が `--dedup` 指定時のみ削除

## Output

- 構造化サマリ: `./reports/<ticker>-<date>-summary.md`
- Cleaned text: `./downloads/<ticker>/<date>-<type>-cleaned.md`
- Metadata JSON: `./manifests/<ticker>-<date>-meta.json`

## Constraints

- 巨大 PDF (>200MB) は **章単位で分割** してから NotebookLM へ upload
- Token 効率のため、表データは markdown table に変換 (PDF table-as-image は OCR 必要、別問題)
- 数値の桁区切り (1,234,567 vs 1.234.567) は提出元に合わせる
- 図表 (グラフ・チャート) は本文 text には含めない、別 image source として扱う候補
