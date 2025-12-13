# ✈️ Travel Planner Agent

AIを活用した旅行計画作成アシスタント。Web検索とLLMを組み合わせて、最新情報に基づいた詳細な旅行プランを自動生成します。

## 🎯 何ができるか

### 1. **AI Agentによる自動プランニング**
- ReActパターンに基づく自律的な旅行計画生成
- ユーザーの条件（目的地、日数、予算、興味テーマ）に基づいて最適なプランを提案

### 2. **Web検索による最新情報の取得**
- SerpAPIを使用したリアルタイムWeb検索
- イベント情報、営業時間、料金、アクセス情報などの最新データを収集
- 検索結果の優先順位付け（公式サイト > 自治体 > 大手メディア > ブログ）

### 3. **詳細な旅程生成**
- 日別・時間帯別（朝/昼/夕/夜）の詳細なスケジュール
- 参照リンク付きの情報提供
- 注意点・要確認事項の明記
- 概算予算の自動計算

### 4. **対話的な編集機能**
- 生成されたプランの修正・カスタマイズ
- 変更履歴の記録
- Memory機能による過去の会話履歴の活用

## 🚀 使い方

### セットアップ

1. **リポジトリのクローン**
```bash
git clone https://github.com/kawauso918/travel-planner-agent.git
cd travel-planner-agent
```

2. **仮想環境の作成と有効化**
```bash
python3 -m venv env
source env/bin/activate  # Windows: env\Scripts\activate
```

3. **依存パッケージのインストール**
```bash
pip install -r requirements.txt
```

4. **環境変数の設定**
`.env.example`を参考に`.env`ファイルを作成し、APIキーを設定してください（詳細は後述）

### アプリケーションの起動

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。

### 入力例

#### 基本的な使用例

**入力条件：**
- 目的地: 京都
- 滞在日数: 3日
- 予算: 50,000円
- 興味テーマ: グルメ、歴史
- 旅行スタイル: normal（標準）
- 出発地点: 東京
- 移動手段: public（公共交通機関）

**出力：**
- Day 1〜3の詳細な旅程（朝/昼/夕/夜の時間帯別）
- 各スポットの概要、所要時間、料金、アクセス情報
- 参照リンク（公式サイトなど）
- 注意点・要確認事項
- 概算予算の内訳（交通費、食事代、体験・入場料、その他）

#### 高度な使用例

**制約条件の指定：**
- ベジタリアン対応のレストラン希望
- 雨天時も楽しめるプラン
- 予約必須のスポットは事前に確認

**Memory機能の活用：**
- Memory ON/OFFの切り替えが可能
- 過去の会話履歴を参照して、よりパーソナライズされた提案

## 🔐 Secretsの設定方法

### 必要なAPIキー

本アプリケーションは以下のAPIキーが必要です：

1. **OpenAI API Key**
   - 用途: LLMによる旅程生成・編集
   - 取得方法: [OpenAI Platform](https://platform.openai.com/api-keys) でアカウント作成後、APIキーを生成

2. **SerpAPI API Key**
   - 用途: Web検索による最新情報の取得
   - 取得方法: [SerpAPI](https://serpapi.com/) でアカウント作成後、APIキーを生成

### 環境変数の設定

#### 方法1: `.env`ファイルを使用（推奨）

プロジェクトルートに`.env`ファイルを作成し、以下の形式で記述してください：

```env
OPENAI_API_KEY=your_openai_api_key_here
SERPAPI_API_KEY=your_serpapi_api_key_here
OPENAI_MODEL=gpt-4
```

**注意：**
- `.env`ファイルは`.gitignore`に含まれているため、Gitにコミットされません
- 実際のAPIキーは記載せず、`.env.example`を参考にしてください

#### 方法2: 環境変数として設定

```bash
export OPENAI_API_KEY=your_openai_api_key_here
export SERPAPI_API_KEY=your_serpapi_api_key_here
export OPENAI_MODEL=gpt-4
```

### セキュリティに関する注意事項

- ⚠️ **APIキーは絶対にGitにコミットしないでください**
- ⚠️ **公開リポジトリにAPIキーを含めないでください**
- ✅ `.env`ファイルは`.gitignore`に含まれています
- ✅ ログ出力時もAPIキーは自動的にマスクされます

## 📸 画面スクリーンショット

![Travel Planner Agent](screenshot.png)

*上記は架空の入力例です。実際の個人情報は含まれていません。*

## 🛠️ 技術スタック

- **フレームワーク**: Streamlit
- **LLM**: OpenAI GPT-4 (LangChain経由)
- **Web検索**: SerpAPI
- **言語**: Python 3.11+
- **主要ライブラリ**:
  - `langchain`, `langchain-openai`, `langchain-core`
  - `pydantic` (データバリデーション)
  - `python-dotenv` (環境変数管理)

## 📁 プロジェクト構成

```
travel-planner-agent/
├── app.py                 # Streamlitアプリケーション
├── requirements.txt       # 依存パッケージ
├── .env.example          # 環境変数のテンプレート
├── README.md             # このファイル
└── src/
    ├── agent.py          # メインエージェントロジック
    ├── config.py         # 設定管理
    ├── logger.py         # ログ管理
    ├── memory.py         # 会話履歴管理
    ├── prompts.py        # プロンプトテンプレート
    ├── schemas.py        # Pydanticスキーマ定義
    ├── utils.py          # ユーティリティ関数
    └── tools/
        ├── web_search.py      # Web検索ツール
        ├── plan_generator.py  # 旅程生成ツール
        └── plan_editor.py     # 旅程編集ツール
```

## 📝 主な機能

- ✅ ReActパターンによる自律的なプランニング
- ✅ リアルタイムWeb検索による最新情報の取得
- ✅ 詳細な旅程生成（日別・時間帯別）
- ✅ 参照リンク付きの情報提供
- ✅ 注意点・要確認事項の自動抽出
- ✅ 概算予算の自動計算
- ✅ 対話的な編集機能
- ✅ Memory機能による会話履歴の活用
- ✅ エラーハンドリングとログ出力
- ✅ 機密情報の自動マスク

## 🐛 トラブルシューティング

### APIキーが認識されない場合

1. `.env`ファイルがプロジェクトルートに存在するか確認
2. 環境変数名が正しいか確認（`OPENAI_API_KEY`, `SERPAPI_API_KEY`）
3. アプリケーションを再起動

### 検索結果が取得できない場合

- SerpAPIのAPIキーが正しく設定されているか確認
- APIの利用制限に達していないか確認
- インターネット接続を確認

### その他のエラー

- ログファイル（`logs/travel_planner_YYYYMMDD.log`）を確認
- エラーメッセージに従って対処

## 📄 ライセンス

このプロジェクトは個人のポートフォリオ用に作成されています。

## 👤 作成者

- GitHub: [@kawauso918](https://github.com/kawauso918)

---

**注意**: このアプリケーションは教育・ポートフォリオ目的で作成されています。商用利用の際は、各APIの利用規約を確認してください。
