# 生成AI活用 提案書ジェネレーター

潜在顧客の **WebサイトURL** を入力するだけで、**サイト調査 + Web検索 + 自社資料RAG + Claude Opus 4.6** を使い、その企業の事業内容・課題に即した「生成AI活用ご提案書」を PowerPoint 形式で自動生成する Streamlit アプリです。

経営コンサルティング事業において、潜在顧客の経営者向けに、初回議論に耐えうる水準の提案書を効率的に作成することを目的としています。

## 生成フロー

```
潜在顧客のWebサイトURL入力
  → 🌐 サイト調査（会社概要・事業内容・ニュース等のページを収集）
  → 🔍 Web検索（Claude 組み込みツールで業界動向・ニュースを補完）
  → 📚 自社サービス資料・支援実績RAG（ローカルフォルダ or アップロード）
  → 🤖 Claude Opus 4.6 で課題仮説・生成AI活用アプローチを検討
  → 📊 PowerPoint スライドを出力
```

## アウトプットの構成

- 企業概要（事業ドメイン・規模・直近トピック）
- 主要事業（セグメント別）
- 主要事業における課題仮説（収集した事実に基づく、企業固有の仮説）
- 生成AI活用の全体観
- 生成AI活用アプローチ案（課題仮説と1対1で対応）
- アプローチ詳細（支援内容・期待効果）
- 導入・計画の進め方（フェーズ別ロードマップ）
- 想定投資規模・ROI試算（任意）
- 類似支援実績（任意）
- 想定される論点・Q&A
- 次のステップ
- Appendix：リサーチ根拠・出典

---

## Docker で起動する（推奨）

### 前提条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) がインストール済み
- Anthropic API キーを取得済み（https://console.anthropic.com/）

### 手順

**① .env ファイルを作成する**

```bash
cp .env.example .env
```

`.env` をテキストエディタで開き、以下を設定します：

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx
REFERENCE_DOCS_PATH=C:/Users/yourname/Documents/proposal-reference-docs
```

> `REFERENCE_DOCS_PATH` は自社のサービス資料・過去の支援実績が入ったフォルダのパス（Windows の場合は `\` の代わりに `/` を使用）。なくても動作します。

**② コンテナを起動する**

```bash
docker compose up --build
```

初回はイメージのビルドに数分かかります。

**③ ブラウザでアクセスする**

```
http://localhost:8501
```

**④ 停止する**

```bash
docker compose down
```

---

## ローカルで直接起動する（Python 環境がある場合）

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 使い方

1. サイドバーで Anthropic API キーを入力（環境変数でも可）
2. サイドバーで提案元（自社）の会社名・資料フォルダを設定（任意）
3. メイン画面で潜在顧客のWebサイトURLを入力（企業名が分かれば任意で入力）
4. 「🚀 提案書を生成する」を押す
5. 生成された提案書サマリーを確認し、PowerPointをダウンロード

## 注意事項

- **サイト調査**: 潜在顧客のコーポレートサイト（トップページ + 会社概要・事業内容・ニュース等のページ）を公開情報の範囲でのみ取得します
- **資料フォルダ**: Docker 起動時は `REFERENCE_DOCS_PATH` で指定したフォルダがコンテナ内の `/docs/reference` にマウントされます
- **ファイル形式**: PDF / DOCX / PPTX / TXT に対応
- **資料なしでも動作**: 自社資料がなくても、サイト調査・Web検索と Claude の知識から提案書を生成します
- **ファイルアップロード**: フォルダが使えない場合はサイドバーからファイルを直接アップロードできます
- **API キー**: 環境変数 `ANTHROPIC_API_KEY` が設定されていればサイドバーへの入力は不要です
- **URLエラー**: 指定したURLにアクセスできない場合はエラーメッセージが表示されます。URLを確認して再度お試しください
