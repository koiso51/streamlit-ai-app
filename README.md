# FASTLabel 提案書作成ツール

クライアント企業名を入力するだけで、**Web 検索 + 社内資料 RAG + Claude Opus 4.6** を使い、PowerPoint 形式の提案書を自動生成する Streamlit アプリです。

## 生成フロー

```
企業名入力
  → 🔍 Web 検索（Claude 組み込みツール）
  → 📚 FASTLabel 社内資料 RAG（ローカルフォルダ or アップロード）
  → 🤖 Claude Opus 4.6 で課題仮説・提案内容を検討
  → 📊 PowerPoint スライド（10枚構成）を出力
```

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
FASTLABEL_DOCS_PATH=C:/Users/oisok/OneDrive/Desktop/Fastlabel
```

> `FASTLABEL_DOCS_PATH` は FASTLabel 資料が入ったフォルダのパス（Windows の場合は `\` の代わりに `/` を使用）

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

## 注意事項

- **資料フォルダ**: Docker 起動時は `FASTLABEL_DOCS_PATH` で指定したフォルダがコンテナ内の `/docs/fastlabel` にマウントされます
- **ファイル形式**: PDF / DOCX / PPTX / TXT に対応
- **資料なしでも動作**: 社内資料がなくても、Web 検索と Claude の知識から提案書を生成します
- **ファイルアップロード**: フォルダが使えない場合はサイドバーからファイルを直接アップロードできます
- **API キー**: 環境変数 `ANTHROPIC_API_KEY` が設定されていればサイドバーへの入力は不要です
