# ✈️ Travel Planner Agent

AIを活用した旅行計画作成アシスタント。Web検索とLLMを組み合わせて、最新情報に基づいた詳細な旅行プランを自動生成します。

## Overview

Travel Planner Agentは、**ReActパターン**に基づく自律的なAIエージェントです。ユーザーが指定した条件（目的地、日数、予算、興味テーマなど）に基づいて、以下の機能を提供します：

- **リアルタイムWeb検索**: SerpAPIを使用して最新のイベント情報、営業時間、料金、アクセス情報を取得
- **詳細な旅程生成**: 日別・時間帯別（朝/昼/夕/夜）の詳細なスケジュールを自動生成
- **パーソナライズ**: RAG（Retrieval-Augmented Generation）によるお気に入りリスト、旅行メモ、過去旅程の活用
- **対話的な編集**: 生成されたプランの修正・カスタマイズ機能
- **Memory機能**: 会話履歴を活用したよりパーソナライズされた提案

## Features

### 差別化ポイント

1. **最新情報の自動取得**
   - 検索結果の優先順位付け（公式サイト > 自治体 > 大手メディア > ブログ）
   - 検索結果0件時の自動クエリ拡張
   - 429エラーやタイムアウト時の適切なフォールバック処理

2. **構造化された出力**
   - テンプレートv2.0準拠の出力順序（旅程→参照リンク→注意点→概算予算）
   - 参照リンク付きの情報提供
   - 注意点・要確認事項の自動抽出

3. **RAGによるパーソナライズ**
   - お気に入りリスト、旅行メモ、過去旅程の管理
   - 関連する個人知識を自動的に旅程生成に反映

4. **堅牢なエラーハンドリング**
   - 例外が発生してもUIが落ちない設計
   - ログ出力による問題追跡
   - 機密情報（APIキー）の自動マスク

## Demo

![Travel Planner Agent](screenshot.png)

*上記は架空の入力例です。実際の個人情報は含まれていません。*

**デモURL**: [Streamlit Community Cloudで公開予定]

## Tech Stack

- **フレームワーク**: Streamlit
- **LLM**: OpenAI GPT-4 (LangChain経由)
- **Web検索**: SerpAPI
- **言語**: Python 3.11+
- **主要ライブラリ**:
  - `langchain`, `langchain-openai`, `langchain-core`
  - `pydantic` (データバリデーション)
  - `python-dotenv` (環境変数管理)
  - `google-search-results` (SerpAPI)

## Architecture

### システム構成図

```
┌─────────────┐
│   User      │
│  (Streamlit)│
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│      Agent (ReAct Pattern)      │
│  ┌───────────────────────────┐  │
│  │ 1. Search Plan            │  │
│  │ 2. Web Search (Tool A)    │  │
│  │ 3. Summarize Results      │  │
│  │ 4. Generate Plan (Tool B) │  │
│  │ 5. Edit Plan (Tool C)     │  │
│  └───────────────────────────┘  │
└──────┬──────────────────────────┘
       │
       ├──► Tool A: Web Search (SerpAPI)
       │    └─ 最新情報の取得
       │
       ├──► Tool B: Plan Generator (LLM)
       │    └─ 旅程Markdown生成
       │
       ├──► Tool C: Plan Editor (LLM)
       │    └─ 旅程の修正・更新
       │
       ├──► Memory (ConversationSummaryBufferMemory)
       │    └─ 会話履歴の管理
       │
       └──► Knowledge Base (RAG)
            └─ お気に入り・メモ・過去旅程
```

### Tools一覧

| Tool | 名称 | 説明 | 実装ファイル |
|------|------|------|------------|
| **Tool A** | Web Search | SerpAPIを使用したリアルタイムWeb検索。イベント情報、営業時間、料金、アクセス情報を取得 | `src/tools/web_search.py` |
| **Tool B** | Plan Generator | 検索結果を要約し、LLMで詳細な旅程Markdownを生成。日別・時間帯別のスケジュールを作成 | `src/tools/plan_generator.py` |
| **Tool C** | Plan Editor | 既存の旅程にユーザー指示を反映して修正。変更履歴を記録 | `src/tools/plan_editor.py` |

### データフロー

1. **入力**: ユーザーが目的地、日数、予算、テーマなどを入力
2. **検索計画**: `build_search_plan`で検索クエリを生成（最大5回）
3. **Web検索**: Tool Aで最新情報を取得
4. **要約**: 検索結果を`SearchBrief`に要約
5. **旅程生成**: Tool Bで詳細な旅程Markdownを生成
6. **出力**: 旅程、参照リンク、注意点、概算予算を表示

## Setup

### Local環境でのセットアップ

#### 1. リポジトリのクローン

```bash
git clone https://github.com/kawauso918/travel-planner-agent.git
cd travel-planner-agent
```

#### 2. 仮想環境の作成と有効化

```bash
python3 -m venv env
source env/bin/activate  # Windows: env\Scripts\activate
```

#### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

#### 4. 環境変数の設定

`.env.example`を参考に`.env`ファイルを作成し、APIキーを設定してください：

```env
OPENAI_API_KEY=your_openai_api_key_here
SERPAPI_API_KEY=your_serpapi_api_key_here
OPENAI_MODEL=gpt-4
```

詳細は[Security](#security)セクションを参照してください。

#### 5. アプリケーションの起動

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。

## Deploy

### Streamlit Community Cloud

1. **GitHubリポジトリを準備**
   - リポジトリをGitHubにプッシュ
   - `requirements.txt`が含まれていることを確認

2. **Streamlit Community Cloudにデプロイ**
   - [Streamlit Community Cloud](https://streamlit.io/cloud)にアクセス
   - GitHubアカウントでログイン
   - 「New app」をクリック
   - リポジトリとブランチを選択
   - Main file path: `app.py`

3. **Secretsの設定**
   - 「Secrets」タブを開く
   - 以下の形式でAPIキーを設定：
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   SERPAPI_API_KEY=your_serpapi_api_key_here
   OPENAI_MODEL=gpt-4
   ```

4. **デプロイ完了**
   - 「Deploy」をクリック
   - デプロイが完了すると、公開URLが生成されます

## Usage

### 入力例

#### 基本的な使用例

**入力条件：**
- 目的地: 京都
- 滞在日数: 3日
- 予算: 50,000円（宿泊費、交通費、食事代、体験・入場料、その他を含む）
- 興味テーマ: グルメ、歴史
- 旅行スタイル: normal（標準）
- 出発地点: 東京
- 移動手段: public（公共交通機関）
- やりたいこと・希望事項: ベジタリアン対応のレストラン希望

**出力例：**

```markdown
# 京都 3日間の旅行プラン

## Day 1

### 朝（9:00-12:00）
**清水寺**
- 概要: 世界遺産の寺院。桜や紅葉の名所として知られる
- 所要時間: 2時間
- 料金: 400円
- アクセス: 京都市バス「清水道」下車、徒歩10分
- 参照: https://www.kiyomizudera.or.jp/

### 昼（12:00-14:00）
**ベジタリアン対応レストラン「Vegan Ramen UZU」**
- 概要: 京都で人気のヴィーガンラーメン店
- 所要時間: 1時間
- 料金: 1,200円
- アクセス: 清水寺から徒歩15分
- 参照: https://uzu-kyoto.com/

### 夕（14:00-18:00）
**祇園・花見小路**
- 概要: 伝統的な街並みが残るエリア
- 所要時間: 2時間
- 料金: 無料（散策）
- アクセス: 京都市バス「祇園」下車

### 夜（18:00-21:00）
**京都タワー**
- 概要: 京都の夜景を楽しめる展望台
- 所要時間: 1時間
- 料金: 800円
- アクセス: JR京都駅から徒歩2分

## Day 2
...

## Day 3
...

---

## 参照リンク

- [清水寺公式サイト](https://www.kiyomizudera.or.jp/)
- [Vegan Ramen UZU](https://uzu-kyoto.com/)
- [京都観光Navi](https://kanko.city.kyoto.lg.jp/)

## 注意点

- 清水寺は混雑が予想されます。早めの訪問を推奨します
- ベジタリアン対応レストランは事前予約を推奨します
- 雨天時は屋内施設を中心にプランを変更することをお勧めします

## 概算予算

| 項目 | 金額 |
|------|------|
| 交通費（東京⇔京都） | 13,000円 |
| 宿泊費（2泊） | 20,000円 |
| 食事代 | 12,000円 |
| 体験・入場料 | 3,000円 |
| その他 | 2,000円 |
| **合計** | **50,000円** |
```

#### 高度な使用例

**RAG機能の活用：**
- お気に入りリストに「清水寺」「金閣寺」を登録
- 旅行メモに「ベジタリアン対応希望」を記録
- 過去旅程を参照して、類似のプランを生成

**Memory機能の活用：**
- Memory ON/OFFの切り替えが可能
- 過去の会話履歴を参照して、よりパーソナライズされた提案

## Security

### APIキーの管理

⚠️ **重要**: APIキーは絶対にGitにコミットしないでください。

#### ローカル環境

1. `.env`ファイルを作成（`.env.example`を参考）
2. `.env`ファイルは`.gitignore`に含まれているため、Gitにコミットされません
3. 実際のAPIキーは記載せず、`.env.example`を参考にしてください

#### Streamlit Community Cloud

1. 「Secrets」タブでAPIキーを設定
2. Secretsは暗号化されて保存されます
3. コード内では`os.getenv()`で環境変数から読み込みます

### ログ出力時の機密情報マスク

- APIキーは自動的にマスクされます（例: `sk-***MASKED***`）
- ログファイルは`logs/`ディレクトリに保存されます
- ログファイルは`.gitignore`に含まれています

### 必要なAPIキー

1. **OpenAI API Key**
   - 用途: LLMによる旅程生成・編集
   - 取得方法: [OpenAI Platform](https://platform.openai.com/api-keys) でアカウント作成後、APIキーを生成

2. **SerpAPI API Key**
   - 用途: Web検索による最新情報の取得
   - 取得方法: [SerpAPI](https://serpapi.com/) でアカウント作成後、APIキーを生成

## License

このプロジェクトは個人のポートフォリオ用に作成されています。

## 👤 作成者

- GitHub: [@kawauso918](https://github.com/kawauso918)

---

**注意**: このアプリケーションは教育・ポートフォリオ目的で作成されています。商用利用の際は、各APIの利用規約を確認してください。
