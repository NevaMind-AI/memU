![MemU Banner](../assets/banner.png)

<div align="center">

# memU

### ファイルシステムは記憶、記憶はエージェントを形づくる

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.com/invite/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](README_en.md) | [中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md)**

</div>

---

memU は AI エージェントのための**記憶ファイルシステム**です。

エージェントが学んだすべてを巨大なプロンプトや不透明なベクトルの塊に押し込むのではなく、memU はコンピュータを整理するのと同じように記憶を整理します——ナビゲート可能で人間が読める Markdown ファイルのツリーとして。

- **`MEMORY.md`** —— エージェントの生きた記憶：ユーザーが誰か、その嗜好、目標、そしてあらゆるソースから抽出された出来事
- **`SKILL.md`** —— 学習したスキルとツールのパターン：何がうまくいったか、何を避けるべきか、繰り返し発生するタスクをどう再現するか
- **`INDEX.md`** —— 目次：すべての記憶ファイルを横断するナビゲーション可能なマップ。読み込む前にどこを見ればよいかをエージェントに伝える
- **エージェントはこれらのファイルを読み書きする**——`memorize()` で新しいソースを書き込み、`retrieve()` で必要に応じて本当に関連する部分だけを読み出す

```txt
memory/
├── INDEX.md              ← 全体のマップ：カテゴリ、ファイル、サマリー
├── MEMORY.md             ← プロフィール、嗜好、目標、主要な出来事
└── skill/
    ├── {skill_name}/
    │   └── SKILL.md       ← 学習したスキルまたはツールのパターン
    └── {another_skill}/
        └── SKILL.md
```

**ファイルシステムは記憶**：階層的で閲覧可能な面であり、すべての記憶がそのソースまで遡れます。
**記憶はエージェントを形づくる**：その面が構造化され自己組織化されているため、受動的なストレージであることをやめ、エージェントがどう考えどう行動するかを形づくる層になります。

---

## 🔄 仕組み

2 つのファイルシステム操作として考えてください：生のソースを整理された記憶に**書き込み**、適切なファイルをエージェントに**読み戻す**。

```
WRITE — memorize()                                         READ — retrieve()
──────────────────────────────────────────────            ──────────────────────────────────────────────
raw files        →  extract  →  files + folders            query  →  walk folders  →  ranked files
─────────────       ─────────    ──────────────            ─────     ────────────     ─────────────
chat logs        →  parse    →  profile / event items      user / task query
documents / URLs →  facts    →  knowledge / skill items       │
images / video   →  caption  →  resources + summaries         ├─ route + scope    → relevant folders (categories)
audio            →  transcribe→ event / knowledge items       ├─ rank by relevance → matching files (items)
tool logs        →  mine      → tool / skill items            └─ trace to source   → original resources
```

**ファイルシステムへの書き込み（`memorize`）**

1. **取り込み（Ingest）** — 各ソースを `Resource`（生のファイル）として、そのモダリティとソースの場所とともに保存する
2. **前処理（Preprocess）** — テキストを解析し、画像/動画にキャプションを付け、音声を文字起こしし、入力を正規化する
3. **抽出（Extract）** — 生のコンテンツを型付きの `MemoryItem`（ファイル）に変換する：profile、event、knowledge、behavior、skill、tool の記憶
4. **整理（Organize）** — アイテムを `MemoryCategory` フォルダに振り分け、相互リンクし、埋め込みを作り、閲覧可能なツリーへ要約する
5. **永続化（Persist）** — 設定されたバックエンドを通じてレコード、関係、埋め込み、フォルダのサマリーを書き込む

**ファイルシステムからの読み込み（`retrieve`）**

6. **検索（Retrieve）** — フォルダをたどり、現在のユーザー、エージェント、セッション、タスクに関連するファイルだけを返す

---

## 🗂️ 記憶ファイルシステム

memU の主要な出力は、ナビゲート可能な記憶のツリーです——フォルダ、ファイル、そしてそれらの背後にあるソース素材——リポジトリ契約を通じて永続化され、`memorize()` と `retrieve()` から辞書として返されます。

```txt
MemoryCategory                       ← フォルダ：進化するサマリーを持つトピック
├── name, description, summary
├── embedding
└── MemoryItem[]                     ← ファイル：型付きのアトミックな記憶
    ├── memory_type: profile | event | knowledge | behavior | skill | tool
    ├── summary, extra, happened_at, embedding
    └── Resource                     ← ソース：この記憶の由来となった生のファイル
        └── url, modality, local_path, caption, embedding
```

| レコード | ファイルシステム上の役割 | 用途 |
|--------|------------------|---------|
| `MemoryCategory` | **フォルダ** — 関連する記憶をまとめ、トピックレベルのサマリーを保持する | 広いクエリ向けにコンパクトなコンテキストを読み込む |
| `MemoryItem` | **ファイル** — サマリーと任意のメタデータを持つ型付きアトミック記憶 | 正確な事実、嗜好、出来事、スキル、ツールパターンを注入する |
| `Resource` | **ソース素材** — 記憶の背後にある元ファイル（キャプション/テキスト付き） | コンテキストをその由来まで遡る |
| `CategoryItem` | **リンク** — アイテムをフォルダ配下に振り分けるエッジ | ソースを再処理せずに関連する記憶をナビゲートする |

これによりエージェントは安定した記憶のファイルシステムを得ます：生のソースは一度取り込めばよく、以降はすべてのソース素材を読み直す代わりに、スコープ付き・ランク付けされたファイルを要求できます。

---

## 🧩 memU が構築するもの

ファイルシステムの各層は構造化レコードとして保存されます：

| 層 | 何を表すか | エージェントが使う理由 |
|-------|--------------------|-------------------|
| **MemoryCategory** | 自動生成されるフォルダ：進化するサマリーを持つトピック | 詳細に踏み込む前に高レベルのコンテキストを読み込む |
| **MemoryItem** | ファイル：型とサマリーを持つアトミックな構造化記憶 | 正確な事実、嗜好、出来事、スキル、ツールパターンを注入する |
| **Resource** | ファイルの背後にあるソース素材：会話、ドキュメント、画像、動画、音声、URL、ファイル | 記憶をその由来まで遡る |
| **CategoryItem** | アイテムをフォルダ配下に振り分けるリンク | ソースを再処理せずに関連する記憶をナビゲートする |
| **Embedding** | フォルダ・ファイル・ソースにまたがるベクトルインデックス | 低レイテンシで関連コンテキストを検索する |

`memorize()` の出力例：

```json
{
  "resource": {
    "id": "res_01",
    "url": "files/launch-meeting.mp4",
    "modality": "video",
    "caption": "A product planning discussion about onboarding and launch risks."
  },
  "items": [
    {
      "id": "mem_01",
      "memory_type": "event",
      "summary": "The team decided to simplify onboarding before the next launch review."
    },
    {
      "id": "mem_02",
      "memory_type": "profile",
      "summary": "The user prefers concise implementation plans with explicit verification steps."
    },
    {
      "id": "mem_03",
      "memory_type": "tool",
      "summary": "Use repository-wide search before editing configuration files to avoid missing duplicated settings."
    }
  ],
  "categories": [
    {
      "id": "cat_01",
      "name": "product_goals",
      "summary": "Current launch priorities, onboarding decisions, and unresolved risks."
    }
  ],
  "relations": [
    { "item_id": "mem_01", "category_id": "cat_01" }
  ]
}
```

その後、エージェントは `retrieve()` を呼び出してスコープ付き・ランク付けされたコンテキストのペイロードを取得できます：

```python
context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What context matters for this launch task?"}}],
    where={"user_id": "123"},
)
```

---

## ⭐️ リポジトリにスターを

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />

memU が役に立つ・面白いと感じたら、GitHub のスター ⭐️ をいただけると大変ありがたいです。

---

## ✨ 主な機能

| 機能 | 説明 |
|------------|-------------|
| 🗂️ **マルチモーダル取り込み** | 会話、ドキュメント、画像、動画、音声、URL、ログ、ローカルファイルを記憶に書き込む |
| 📁 **記憶ファイルシステム** | フォルダ（カテゴリ）、ファイル（アイテム）、ソース素材、リンク、サマリー、埋め込みを永続化する |
| 🧠 **型付き記憶の抽出** | 生のソースから profile、event、knowledge、behavior、skill、tool の記憶を抽出する |
| 🧭 **自己組織化フォルダ** | 手動タグ付けなしでカテゴリ、リンク、サマリー、埋め込みを自動構築する |
| 🤖 **エージェント対応の検索** | 任意のエージェントワークフローに注入できる、スコープ付き・ランク付けされたコンテキストを読み出す |
| 🧱 **プラグイン可能なストレージ** | 同一のリポジトリ契約で in-memory、SQLite、Postgres バックエンドを使い分ける |
| 🔀 **プロファイルベースの LLM ルーティング** | 設定可能な LLM プロファイルでチャット、埋め込み、ビジョン、文字起こしの処理をルーティングする |

---

## 🎯 ユースケース

### 1. **会話の記憶**
*チャットログをユーザーの嗜好、目標、出来事、関係性のコンテキストに変える。*

```python
await service.memorize(
    resource_url="examples/resources/conversations/conv1.json",
    modality="conversation",
    user={"user_id": "123"},
)

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What should I remember about this user?"}}],
    where={"user_id": "123"},
)
```

### 2. **コーディングエージェント向けのワークスペースコンテキスト**
*ドキュメント、PR メモ、ログ、設計判断を再利用可能なプロジェクト記憶に変える。*

```python
await service.memorize(resource_url="docs/architecture.md", modality="document")
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "How should I structure this module?"}}],
)
```

### 3. **マルチモーダルなナレッジ層**
*ドキュメント、スクリーンショット、画像、動画、音声メモから検索可能な事実を抽出する。*

```python
await service.memorize(resource_url="examples/resources/docs/doc1.txt", modality="document")
await service.memorize(resource_url="examples/resources/images/image1.png", modality="image")
# Audio is supported for your own .mp3/.wav/.m4a files.
await service.memorize(resource_url="meeting-audio.mp3", modality="audio")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What matters for the next research plan?"}}],
)
```

### 4. **ツールとエージェントの学習**
*実行トレースをツール記憶に変え、将来のエージェントにいつツールを使うべきか・どんな失敗を避けるべきかを伝える。*

```python
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "Which tools worked for config editing?"}}],
)
```

---

## 🗂️ アーキテクチャ

記憶ファイルシステムは、閲覧できるほど階層的であり、直接検索できるほど構造化されています：

<img width="100%" alt="structure" src="../assets/structure.png" />

| 層 | 主な役割 | 検索での役割 |
|-------|--------------|----------------|
| **Category（フォルダ）** | トピックレベルのサマリーを維持する | 広いクエリ向けにコンパクトなコンテキストを組み立てる |
| **Item（ファイル）** | 型付きのアトミック記憶を保存する | 正確な事実、出来事、嗜好、スキル、ツールパターンを読み込む |
| **Resource（ソース）** | ソース素材とキャプションを保持する | アイテム/カテゴリのサマリーで不十分なとき元のコンテキストを呼び戻す |

`MemoryService`、ワークフローパイプライン、ストレージバックエンド、LLM ルーティングのランタイムビューについては [docs/architecture.md](../docs/architecture.md) を参照してください。

---

## 🚀 クイックスタート

### オプション 1：クラウド版

👉 **[memu.so](https://memu.so)** — 取り込み、構造化記憶、検索をマネージドで提供するホスト型 API

エンタープライズ導入：**info@nevamind.ai**

#### Cloud API (v3)

| Base URL | `https://api.memu.so` |
|----------|----------------------|
| Auth | `Authorization: Bearer <token>` |

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v3/memory/memorize` | 生データを取り込み構造化記憶を構築する |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | 処理ステータスを確認する |
| `POST` | `/api/v3/memory/categories` | 自動生成されたカテゴリを一覧する |
| `POST` | `/api/v3/memory/retrieve` | エージェントのコンテキストを得るために記憶を検索する |

📚 **[完全な API ドキュメント](https://memu.pro/docs#cloud-version)**

---

### オプション 2：セルフホスト

#### インストール

本リポジトリのクローンから：

```bash
uv sync
# または、フルの開発セットアップ：
make install
```

公開パッケージをインストールする場合：

```bash
pip install memu-py
```

> **要件**：Python 3.13+。デフォルトの例は OpenAI を使うため、`OPENAI_API_KEY` を設定するか、`llm_profiles` で別のプロバイダーを渡してください。

**インメモリのスモークスクリプトを実行：**
```bash
export OPENAI_API_KEY=your_key
cd tests
uv run python test_inmemory.py
```

**PostgreSQL + pgvector で実行：**
```bash
uv sync --extra postgres
docker run -d --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

export OPENAI_API_KEY=your_key
export POSTGRES_DSN=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/memu
cd tests
uv run python test_postgres.py
```

---

### カスタム LLM と埋め込みプロバイダー

```python
from memu import MemUService

service = MemUService(
    llm_profiles={
        "default": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "your_key",
            "chat_model": "qwen3-max",
            "client_backend": "sdk"
        },
        "embedding": {
            "base_url": "https://api.voyageai.com/v1",
            "api_key": "your_key",
            "embed_model": "voyage-3.5-lite"
        }
    },
)
```

---

### OpenRouter 連携

```python
from memu import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openrouter",
            "client_backend": "httpx",
            "base_url": "https://openrouter.ai",
            "api_key": "your_key",
            "chat_model": "anthropic/claude-3.5-sonnet",
            "embed_model": "openai/text-embedding-3-small",
        },
    },
    database_config={"metadata_store": {"provider": "inmemory"}},
)
```

---

## 📖 コア API

### `memorize()` — 生データを構造化する

<img width="100%" alt="memorize" src="../assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",    # ローカルファイルパスまたは HTTP URL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"},            # 任意：ユーザーやエージェントにスコープを限定
)
# 処理完了後に返る：
# { "resource": {...}, "items": [...], "categories": [...], "relations": [...] }
```

- 生の入力を型付きのメモリアイテムに変換する
- 手動タグ付けなしでアイテムを分類し埋め込みを作る
- ソースリソースとアイテム–カテゴリ関係を保持する

---

### `retrieve()` — エージェントのコンテキストを読み込む

<img width="100%" alt="retrieve" src="../assets/retrieve.png" />

```python
# 検索戦略は retrieve_config でサービスに一度だけ設定します：
#   MemoryService(retrieve_config={"method": "rag"})   # ベクトル優先の想起
#   MemoryService(retrieve_config={"method": "llm"})   # LLM ランク付けの想起
result = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What are their preferences?"}}],
    where={"user_id": "123"},   # スコープフィルタ
)
# 返り値：
# {
#   "needs_retrieval": true,
#   "original_query": "...",
#   "rewritten_query": "...",
#   "next_step_query": "...",
#   "categories": [...],
#   "items": [...],
#   "resources": [...]
# }
```

| `retrieve_config.method` | 動作 | コスト | 適した用途 |
|--------------------------|----------|------|----------|
| `rag` | ベクトル優先のカテゴリ/アイテム/リソース想起。任意の LLM ルーティングと充足性チェックがデフォルトで有効 | `route_intention` と `sufficiency_check` を無効にしない限り、埋め込みに加えて LLM 呼び出し | 推論を制御可能にした高速なスコープ想起 |
| `llm` | LLM がランク付けするカテゴリ/アイテム/リソース想起 | 各階層での LLM ランク付け | より深い意味的ランク付け |

---

## 💡 サンプルワークフロー

### 学び続けるアシスタント
```bash
export OPENAI_API_KEY=your_key
uv run python examples/example_1_conversation_memory.py
```
嗜好を自動的に抽出し、関係モデルを構築し、将来の会話で関連コンテキストを浮かび上がらせます。

### 自己改善するエージェント
```bash
uv run python examples/example_2_skill_extraction.py
```
エージェントの行動を監視し、成功と失敗のパターンを特定し、経験からスキルガイドを自動生成します。

### マルチモーダル・コンテキストビルダー
```bash
uv run python examples/example_3_multimodal_memory.py
```
テキスト、画像、ドキュメントを自動的に相互参照し、統一された記憶層にまとめます。

---

## 📊 パフォーマンス

memU は Locomo ベンチマークのすべての推論タスクで **平均 92.09% の精度** を達成しています。

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

詳細な結果を見る：[memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 エコシステム

| リポジトリ | 説明 |
|------------|-------------|
| **[memU](https://github.com/NevaMind-AI/memU)** | コアの記憶ファイルシステム —— 取り込み、抽出、検索 |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | リアルタイム同期と webhook トリガーを備えたバックエンド |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | 記憶を閲覧・監視するためのビジュアルダッシュボード |

**クイックリンク：**
- 🚀 [MemU Cloud を試す](https://app.memu.so/quick-start)
- 📚 [API ドキュメント](https://memu.pro/docs)
- 💬 [Discord コミュニティ](https://discord.com/invite/hQZntfGsbJ)

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
<a href="https://clawdchat.ai/"><img src="../assets/partners/Clawdchat.png" alt="Clawdchat" height="40" style="margin: 10px;"></a>

</div>

---

## 🤝 コントリビュート

```bash
# フォークしてクローン
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# 開発依存をインストール
make install

# 送信前に品質チェックを実行
make check
```

詳しいガイドラインは [CONTRIBUTING.md](../CONTRIBUTING.md) を参照してください。

**前提条件：** Python 3.13+、[uv](https://github.com/astral-sh/uv)、Git

---

## 📄 ライセンス

[Apache License 2.0](../LICENSE.txt)

---

## 🌍 コミュニティ

- **GitHub Issues**：[バグ報告と機能リクエスト](https://github.com/NevaMind-AI/memU/issues)
- **Discord**：[コミュニティに参加](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**：[@memU_ai をフォロー](https://x.com/memU_ai)
- **連絡先**：info@nevamind.ai

---

<div align="center">

⭐ **GitHub でスターを** つけて、新リリースの通知を受け取りましょう！

</div>
