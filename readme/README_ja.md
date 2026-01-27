![MemU Banner](../assets/banner.png)

<div align="center">

# MemU

### AIエージェントのための常時稼働プロアクティブメモリ

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](README_en.md) | [中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md)**

</div>

---

MemUは、継続的に学習し、予測し、適応する**7×24プロアクティブメモリフレームワーク**です。受動的なLLMバックエンドを、明示的なクエリなしに洞察を表示し、ニーズを予測し、コンテキストを進化させる**常時稼働メモリ**を持つインテリジェントエージェントに変換します。

---

## ⭐️ リポジトリにスターを

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />
MemUが役立つまたは興味深いと思われた場合は、GitHub Star ⭐️をいただけると大変嬉しいです。

---

## ✨ コア機能

| 機能 | 説明 |
|------|------|
| 🔄 **継続的学習** | 会話、ドキュメント、アクションなど、あらゆるインタラクションから7×24でメモリを抽出 |
| 🎯 **プロアクティブ検索** | 問い合わせ前に情報ニーズを予測し、関連コンテキストを自動的に表示 |
| 🧠 **コンテキスト進化** | 使用パターンと新興トピックに基づいてメモリ構造がリアルタイムで適応 |
| 🔍 **デュアルインテリジェンス** | 高速な埋め込みベースの呼び出し + 深いLLM推論による包括的な理解 |
| 🎨 **マルチモーダル認識** | テキスト、画像、音声、ビデオ全体の統合メモリ—見たもの聞いたものを記憶 |

---

## 🔄 プロアクティブメモリの仕組み

クエリを待つ従来の検索システムとは異なり、MemUは**継続モード**で動作します：

### パッシブ vs プロアクティブメモリ

| 従来のRAG | MemUプロアクティブメモリ |
|-----------|-------------------------|
| ❌ 明示的なクエリを待つ | ✅ コンテキストを継続的に監視 |
| ❌ リアクティブな情報検索 | ✅ 情報ニーズを予測 |
| ❌ 静的なナレッジベース | ✅ 自己進化するメモリ構造 |
| ❌ 一回限りの処理 | ✅ 常時稼働の学習パイプライン |

### プロアクティブメモリのライフサイクル
```
┌─────────────────────────────────────────────────┐
│  1. 継続的な取り込み                              │
│  └─ すべての会話、ドキュメント、アクションを        │
│     7×24で自動処理                               │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  2. リアルタイム抽出                              │
│  └─ 即座のメモリアイテム作成                       │
│     バッチ遅延なし、即座に利用可能                  │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  3. プロアクティブな構造化                         │
│  └─ 進化するトピックへの自動分類                    │
│     階層的な組織は使用状況に適応                    │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  4. 予測的な検索                                  │
│  └─ プロンプトなしで関連メモリを表示                │
│     コンテキストに応じた提案と洞察                  │
└─────────────────────────────────────────────────┘
```

---

## 🎯 プロアクティブなユースケース

### 1. **コンテキストアシスタンス**
*エージェントが会話コンテキストを監視し、関連メモリをプロアクティブに表示*
```python
# ユーザーがトピックについて話し始める
ユーザー: "あのプロジェクトのことを考えていて..."

# MemUが明示的なクエリなしで自動検索:
- 以前のプロジェクトディスカッション
- 関連する好みと制約
- 過去の決定とその結果
- 関連するドキュメントとリソース

エージェント: "ダッシュボードの再設計での以前の作業に基づいて、
              Material UIコンポーネントを好まれていたようですね..."
```

### 2. **予測的な準備**
*エージェントがパターンに基づいて今後のニーズを予測*
```python
# 朝のルーチン検出
ユーザーが午前9時（通常時間）にログイン

# MemUがプロアクティブに表示:
- デイリースタンドアップの話題
- 一晩の通知サマリー
- 過去の行動に基づく優先タスク
- 昨日の作業からの関連コンテキスト

エージェント: "おはようございます！今日の関連情報です..."
```

### 3. **自律的なメモリ管理**
*手動介入なしでシステムが自己組織化*
```python
# インタラクションが蓄積されるにつれて:
✓ 新興トピックのための新しいカテゴリを自動作成
✓ モダリティ全体で関連メモリを統合
✓ パターンを特定し、より高いレベルの洞察を抽出
✓ 履歴を保持しながら古い情報を削除

# 結果: 常に最適化されたメモリ構造
```

---

## 🗂️ 階層メモリアーキテクチャ

MemUの3層システムは、**リアクティブクエリ**と**プロアクティブコンテキストロード**の両方を可能にします：

<img width="100%" alt="structure" src="../assets/structure.png" />

| レイヤー | リアクティブ使用 | プロアクティブ使用 |
|---------|-----------------|-------------------|
| **リソース** | 元データへの直接アクセス | 新パターンのバックグラウンド監視 |
| **アイテム** | ターゲットを絞った事実検索 | 進行中のインタラクションからのリアルタイム抽出 |
| **カテゴリ** | サマリーレベルの概要 | 予測のための自動コンテキスト組み立て |

**プロアクティブな利点：**
- **自動分類**：新しいメモリがトピックに自己組織化
- **パターン検出**：システムが繰り返し現れるテーマを特定
- **コンテキスト予測**：次に必要な情報を予測

---

## 🚀 クイックスタート

### オプション1：クラウドバージョン

プロアクティブメモリを即座に体験：

👉 **[memu.so](https://memu.so)** - 7×24継続学習を備えたホストサービス

カスタムプロアクティブワークフローを含むエンタープライズデプロイメントについては、**info@nevamind.ai** にお問い合わせください

#### クラウドAPI (v3)

| ベースURL | `https://api.memu.so` |
|-----------|----------------------|
| 認証 | `Authorization: Bearer YOUR_API_KEY` |

| メソッド | エンドポイント | 説明 |
|---------|--------------|------|
| `POST` | `/api/v3/memory/memorize` | 継続学習タスクを登録 |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | リアルタイム処理ステータスを確認 |
| `POST` | `/api/v3/memory/categories` | 自動生成されたカテゴリを一覧表示 |
| `POST` | `/api/v3/memory/retrieve` | メモリをクエリ（プロアクティブコンテキストロードをサポート） |

📚 **[完全なAPIドキュメント](https://memu.pro/docs#cloud-version)**

---

### オプション2：セルフホスト

#### インストール
```bash
pip install -e .
```

#### 基本例

> **要件**：Python 3.13+ と OpenAI APIキー

**継続学習をテスト**（インメモリ）：
```bash
export OPENAI_API_KEY=your_api_key
cd tests
python test_inmemory.py
```

**永続ストレージでテスト**（PostgreSQL）：
```bash
# pgvectorを含むPostgreSQLを起動
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 継続学習テストを実行
export OPENAI_API_KEY=your_api_key
cd tests
python test_postgres.py
```

両方の例は**プロアクティブメモリワークフロー**を示しています：
1. **継続的な取り込み**：複数のファイルを順次処理
2. **自動抽出**：即座のメモリ作成
3. **プロアクティブ検索**：コンテキストに応じたメモリ表示

実装の詳細については [`tests/test_inmemory.py`](../tests/test_inmemory.py) と [`tests/test_postgres.py`](../tests/test_postgres.py) を参照してください。

---

### カスタムLLMと埋め込みプロバイダー

MemUはOpenAI以外のカスタムLLMと埋め込みプロバイダーをサポートしています。`llm_profiles`で設定：
```python
from memu import MemUService

service = MemUService(
    llm_profiles={
        # LLM操作のデフォルトプロファイル
        "default": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "your_api_key",
            "chat_model": "qwen3-max",
            "client_backend": "sdk"  # "sdk" または "http"
        },
        # 埋め込み用の別プロファイル
        "embedding": {
            "base_url": "https://api.voyageai.com/v1",
            "api_key": "your_voyage_api_key",
            "embed_model": "voyage-3.5-lite"
        }
    },
    # ... その他の設定
)
```

---

### OpenRouter統合

MemUは[OpenRouter](https://openrouter.ai)をモデルプロバイダーとしてサポートし、単一のAPIを通じて複数のLLMプロバイダーにアクセスできます。

#### 設定
```python
from memu import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openrouter",
            "client_backend": "httpx",
            "base_url": "https://openrouter.ai",
            "api_key": "your_openrouter_api_key",
            "chat_model": "anthropic/claude-3.5-sonnet",  # 任意のOpenRouterモデル
            "embed_model": "openai/text-embedding-3-small",  # 埋め込みモデル
        },
    },
    database_config={
        "metadata_store": {"provider": "inmemory"},
    },
)
```

#### 環境変数

| 変数 | 説明 |
|------|------|
| `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) からのOpenRouter APIキー |

#### サポートされている機能

| 機能 | ステータス | 注記 |
|------|-----------|------|
| チャット補完 | サポート済み | 任意のOpenRouterチャットモデルで動作 |
| 埋め込み | サポート済み | OpenRouter経由でOpenAI埋め込みモデルを使用 |
| ビジョン | サポート済み | ビジョン対応モデルを使用（例：`openai/gpt-4o`） |

#### OpenRouterテストの実行
```bash
export OPENROUTER_API_KEY=your_api_key

# フルワークフローテスト（メモリ化 + 検索）
python tests/test_openrouter.py

# 埋め込み固有のテスト
python tests/test_openrouter_embedding.py

# ビジョン固有のテスト
python tests/test_openrouter_vision.py
```

完全な動作例については [`examples/example_4_openrouter_memory.py`](../examples/example_4_openrouter_memory.py) を参照してください。

---

## 📖 コアAPI

### `memorize()` - 継続学習パイプライン

入力をリアルタイムで処理し、メモリを即座に更新：

<img width="100%" alt="memorize" src="../assets/memorize.png" />
```python
result = await service.memorize(
    resource_url="path/to/file.json",  # ファイルパスまたはURL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"}             # オプション：ユーザーにスコープ
)

# 抽出されたメモリを即座に返す:
{
    "resource": {...},      # 保存されたリソースメタデータ
    "items": [...],         # 抽出されたメモリアイテム（即座に利用可能）
    "categories": [...]     # 自動更新されたカテゴリ構造
}
```

**プロアクティブ機能：**
- 遅延ゼロの処理—メモリが即座に利用可能
- 手動タグ付けなしの自動分類
- パターン検出のための既存メモリとの相互参照

### `retrieve()` - デュアルモードインテリジェンス

MemUは**プロアクティブコンテキストロード**と**リアクティブクエリ**の両方をサポート：

<img width="100%" alt="retrieve" src="../assets/retrieve.png" />

#### RAGベースの検索 (`method="rag"`)

埋め込みを使用した高速な**プロアクティブコンテキスト組み立て**：

- ✅ **インスタントコンテキスト**：サブ秒のメモリ表示
- ✅ **バックグラウンド監視**：LLMコストなしで継続的に実行可能
- ✅ **類似度スコアリング**：最も関連性の高いメモリを自動的に特定

#### LLMベースの検索 (`method="llm"`)

複雑なコンテキストのための深い**予測的推論**：

- ✅ **意図予測**：LLMがユーザーが尋ねる前にニーズを推測
- ✅ **クエリ進化**：コンテキストの発展に応じて検索を自動的に改善
- ✅ **早期終了**：十分なコンテキストが収集されたら停止

#### 比較

| 側面 | RAG（高速コンテキスト） | LLM（深い推論） |
|------|----------------------|----------------|
| **速度** | ⚡ ミリ秒 | 🐢 秒 |
| **コスト** | 💰 埋め込みのみ | 💰💰 LLM推論 |
| **プロアクティブ使用** | 継続的な監視 | トリガーされたコンテキストロード |
| **最適な用途** | リアルタイムの提案 | 複雑な予測 |

#### 使用方法
```python
# コンテキスト履歴を含むプロアクティブ検索
result = await service.retrieve(
    queries=[
        {"role": "user", "content": {"text": "彼らの好みは何ですか？"}},
        {"role": "user", "content": {"text": "仕事の習慣について教えて"}}
    ],
    where={"user_id": "123"},  # オプション：スコープフィルター
    method="rag"  # または "llm" でより深い推論
)

# コンテキストに応じた結果を返す:
{
    "categories": [...],     # 関連トピック領域（自動優先順位付け）
    "items": [...],          # 具体的なメモリファクト
    "resources": [...],      # 追跡可能な元ソース
    "next_step_query": "..." # 予測されたフォローアップコンテキスト
}
```

**プロアクティブフィルタリング**：`where`を使用して継続的な監視のスコープを設定：
- `where={"user_id": "123"}` - ユーザー固有のコンテキスト
- `where={"agent_id__in": ["1", "2"]}` - マルチエージェント調整
- `where`を省略してグローバルコンテキスト認識

> 📚 **完全なAPIドキュメント**については、[SERVICE_API.md](../docs/SERVICE_API.md) を参照 - プロアクティブワークフローパターン、パイプライン設定、リアルタイム更新処理を含む。

---

## 💡 プロアクティブシナリオ

### 例1：常に学習するアシスタント

明示的なメモリコマンドなしで、すべてのインタラクションから継続的に学習：
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_1_conversation_memory.py
```

**プロアクティブな動作：**
- カジュアルな言及から好みを自動的に抽出
- インタラクションパターンから関係モデルを構築
- 将来の会話で関連コンテキストを表示
- 学習した好みに基づいてコミュニケーションスタイルを適応

**最適な用途：** パーソナルAIアシスタント、記憶するカスタマーサポート、ソーシャルチャットボット

---

### 例2：自己改善エージェント

実行ログから学習し、最適化をプロアクティブに提案：
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_2_skill_extraction.py
```

**プロアクティブな動作：**
- エージェントのアクションと結果を継続的に監視
- 成功と失敗のパターンを特定
- 経験からスキルガイドを自動生成
- 類似の将来のタスクに対する戦略をプロアクティブに提案

**最適な用途：** DevOps自動化、エージェントの自己改善、ナレッジキャプチャ

---

### 例3：マルチモーダルコンテキストビルダー

包括的なコンテキストのために異なる入力タイプ全体でメモリを統合：
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_3_multimodal_memory.py
```

**プロアクティブな動作：**
- テキスト、画像、ドキュメントを自動的に相互参照
- モダリティ全体で統一された理解を構築
- 関連トピックについて議論する際に視覚的コンテキストを表示
- 複数のソースを組み合わせて情報ニーズを予測

**最適な用途：** ドキュメントシステム、学習プラットフォーム、研究アシスタント

---

## 📊 パフォーマンス

MemUは、すべての推論タスクでLocomoベンチマークで**92.09%の平均精度**を達成し、信頼性の高いプロアクティブメモリ操作を実証しています。

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

詳細な実験データを見る：[memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 エコシステム

| リポジトリ | 説明 | プロアクティブ機能 |
|-----------|------|------------------|
| **[memU](https://github.com/NevaMind-AI/memU)** | コアプロアクティブメモリエンジン | 7×24学習パイプライン、自動分類 |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | 継続同期を備えたバックエンド | リアルタイムメモリ更新、webhookトリガー |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | ビジュアルメモリダッシュボード | ライブメモリ進化モニタリング |

**クイックリンク：**
- 🚀 [MemU Cloudを試す](https://app.memu.so/quick-start)
- 📚 [APIドキュメント](https://memu.pro/docs)
- 💬 [Discordコミュニティ](https://discord.gg/memu)

---

## 🤝 パートナー

<div align="center">

<a href="https://github.com/TEN-framework/ten-framework"><img src="https://avatars.githubusercontent.com/u/113095513?s=200&v=4" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://openagents.org"><img src="../assets/partners/openagents.png" alt="OpenAgents" height="40" style="margin: 10px;"></a>
<a href="https://github.com/milvus-io/milvus"><img src="https://miro.medium.com/v2/resize:fit:2400/1*-VEGyAgcIBD62XtZWavy8w.png" alt="Milvus" height="40" style="margin: 10px;"></a>
<a href="https://xroute.ai/"><img src="../assets/partners/xroute.png" alt="xRoute" height="40" style="margin: 10px;"></a>
<a href="https://jaaz.app/"><img src="../assets/partners/jazz.png" alt="Jazz" height="40" style="margin: 10px;"></a>
<a href="https://github.com/Buddie-AI/Buddie"><img src="../assets/partners/buddie.png" alt="Buddie" height="40" style="margin: 10px;"></a>
<a href="https://github.com/bytebase/bytebase"><img src="../assets/partners/bytebase.png" alt="Bytebase" height="40" style="margin: 10px;"></a>
<a href="https://github.com/LazyAGI/LazyLLM"><img src="../assets/partners/LazyLLM.png" alt="LazyLLM" height="40" style="margin: 10px;"></a>

</div>

---

## 🤝 コントリビュート方法

コミュニティからのコントリビュートを歓迎します！バグの修正、機能の追加、ドキュメントの改善など、あなたの助けに感謝します。

### はじめに

MemUへのコントリビュートを開始するには、開発環境をセットアップする必要があります：

#### 前提条件
- Python 3.13+
- [uv](https://github.com/astral-sh/uv)（Pythonパッケージマネージャー）
- Git

#### 開発環境のセットアップ
```bash
# 1. リポジトリをフォークしてクローン
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# 2. 開発依存関係をインストール
make install
```

`make install` コマンドは：
- `uv`を使用して仮想環境を作成
- すべてのプロジェクト依存関係をインストール
- コード品質チェックのためのpre-commitフックをセットアップ

#### 品質チェックの実行

コントリビュートを提出する前に、コードがすべての品質チェックに合格していることを確認してください：
```bash
make check
```

`make check` コマンドは：
- **ロックファイル検証**：`pyproject.toml`の一貫性を確認
- **Pre-commitフック**：Ruffでコードをリント、Blackでフォーマット
- **型チェック**：静的型分析のための`mypy`を実行
- **依存関係分析**：`deptry`で古い依存関係を検索

### コントリビューションガイドライン

詳細なコントリビューションガイドライン、コード標準、開発プラクティスについては、[CONTRIBUTING.md](../CONTRIBUTING.md) を参照してください。

**クイックヒント：**
- 各機能またはバグ修正用に新しいブランチを作成
- 明確なコミットメッセージを書く
- 新機能にテストを追加
- 必要に応じてドキュメントを更新
- プッシュ前に `make check` を実行

---

## 📄 ライセンス

[Apache License 2.0](../LICENSE.txt)

---

## 🌍 コミュニティ

- **GitHub Issues**：[バグを報告 & 機能をリクエスト](https://github.com/NevaMind-AI/memU/issues)
- **Discord**：[コミュニティに参加](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**：[@memU_ai をフォロー](https://x.com/memU_ai)
- **お問い合わせ**：info@nevamind.ai

---

<div align="center">

⭐ **GitHubでスターを付けて**、新しいリリースの通知を受け取りましょう！

</div>
