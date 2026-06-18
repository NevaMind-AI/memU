![MemU Banner](../assets/banner.png)

<div align="center">

# memU

### 파일 시스템은 메모리, 메모리는 에이전트를 빚는다

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.com/invite/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](README_en.md) | [中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md)**

</div>

---

memU는 AI 에이전트를 위한 **메모리 파일 시스템**입니다.

에이전트가 학습한 모든 것을 거대한 프롬프트나 불투명한 벡터 덩어리로 짓눌러 넣는 대신, memU는 컴퓨터를 정리하듯 메모리를 정리합니다 — 탐색 가능하고 사람이 읽을 수 있는 Markdown 파일 트리로.

- **`MEMORY.md`** — 에이전트의 살아 있는 메모리: 사용자가 누구인지, 그 선호, 목표, 그리고 모든 소스에서 추출한 사건
- **`SKILL.md`** — 학습한 스킬과 도구 패턴: 무엇이 효과적이었는지, 무엇을 피해야 하는지, 반복되는 작업을 어떻게 재현하는지
- **`INDEX.md`** — 목차: 모든 메모리 파일을 가로지르는 탐색 가능한 지도로, 읽기 전에 어디를 봐야 하는지 에이전트에게 알려줍니다
- **에이전트는 이 파일들을 읽고 씁니다** — `memorize()`로 새 소스를 그 안에 쓰고, `retrieve()`로 필요할 때 정말 관련 있는 부분만 읽습니다

```txt
memory/
├── INDEX.md              ← 전체 지도: 카테고리, 파일, 요약
├── MEMORY.md             ← 프로필, 선호, 목표, 주요 사건
└── skill/
    ├── {skill_name}/
    │   └── SKILL.md       ← 학습한 스킬 또는 도구 패턴
    └── {another_skill}/
        └── SKILL.md
```

**파일 시스템은 메모리**: 모든 메모리가 그 소스까지 거슬러 올라갈 수 있는, 계층적이고 탐색 가능한 표면입니다.
**메모리는 에이전트를 빚습니다**: 그 표면이 구조화되고 스스로 조직화되기 때문에, 수동적 저장소이기를 멈추고 에이전트가 어떻게 생각하고 행동하는지를 빚는 계층이 됩니다.

---

## 🔄 작동 방식

두 가지 파일 시스템 작업으로 생각하세요: 원본 소스를 정리된 메모리에 **쓰기**, 그리고 알맞은 파일을 에이전트로 다시 **읽기**.

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

**파일 시스템에 쓰기(`memorize`)**

1. **수집(Ingest)** — 각 소스를 모달리티와 소스 위치와 함께 `Resource`(원본 파일)로 저장합니다
2. **전처리(Preprocess)** — 텍스트를 파싱하고, 이미지/비디오에 캡션을 달고, 오디오를 전사하고, 입력을 정규화합니다
3. **추출(Extract)** — 원본 콘텐츠를 타입이 지정된 `MemoryItem`(파일)으로 변환합니다: profile, event, knowledge, behavior, skill, tool 메모리
4. **조직화(Organize)** — 아이템을 `MemoryCategory` 폴더로 분류하고, 상호 링크하고, 임베딩하고, 탐색 가능한 트리로 요약합니다
5. **영속화(Persist)** — 설정된 백엔드를 통해 레코드, 관계, 임베딩, 폴더 요약을 기록합니다

**파일 시스템에서 읽기(`retrieve`)**

6. **검색(Retrieve)** — 폴더를 탐색하여 현재 사용자, 에이전트, 세션 또는 태스크에 관련된 파일만 반환합니다

---

## 🗂️ 메모리 파일 시스템

memU의 주요 산출물은 탐색 가능한 메모리 트리입니다 — 폴더, 파일, 그리고 그 뒤에 있는 소스 산출물 — 리포지토리 계약을 통해 영속화되며 `memorize()`와 `retrieve()`에서 딕셔너리로 반환됩니다.

```txt
MemoryCategory                       ← 폴더: 진화하는 요약을 가진 주제
├── name, description, summary
├── embedding
└── MemoryItem[]                     ← 파일: 타입이 지정된 원자적 메모리
    ├── memory_type: profile | event | knowledge | behavior | skill | tool
    ├── summary, extra, happened_at, embedding
    └── Resource                     ← 소스: 이 메모리가 비롯된 원본 파일
        └── url, modality, local_path, caption, embedding
```

| 레코드 | 파일 시스템 역할 | 사용 목적 |
|--------|------------------|---------|
| `MemoryCategory` | **폴더** — 관련 메모리를 묶고 주제 수준 요약을 유지 | 폭넓은 질의를 위해 간결한 컨텍스트를 로드 |
| `MemoryItem` | **파일** — 요약과 선택적 메타데이터를 가진 타입 지정 원자 메모리 | 정확한 사실, 선호, 사건, 스킬, 도구 패턴을 주입 |
| `Resource` | **소스 산출물** — 메모리 뒤의 원본 파일(캡션/텍스트 포함) | 컨텍스트를 그 출처까지 추적 |
| `CategoryItem` | **링크** — 아이템을 폴더 아래에 분류하는 엣지 | 소스를 재처리하지 않고 관련 메모리를 탐색 |

이를 통해 에이전트는 안정적인 메모리 파일 시스템을 얻습니다: 원본 소스는 한 번만 수집하면 되고, 이후에는 모든 소스 산출물을 다시 읽는 대신 범위가 지정되고 순위가 매겨진 파일을 요청할 수 있습니다.

---

## 🧩 memU가 구축하는 것

파일 시스템의 각 계층은 구조화 레코드로 저장됩니다:

| 계층 | 무엇을 나타내는가 | 에이전트가 사용하는 이유 |
|-------|--------------------|-------------------|
| **MemoryCategory** | 자동 생성 폴더: 진화하는 요약을 가진 주제 | 세부로 파고들기 전에 상위 수준 컨텍스트를 로드 |
| **MemoryItem** | 파일: 타입과 요약을 가진 원자적 구조화 메모리 | 정확한 사실, 선호, 사건, 스킬, 도구 패턴을 주입 |
| **Resource** | 파일 뒤의 소스 산출물: 대화, 문서, 이미지, 비디오, 오디오, URL, 파일 | 메모리를 그 출처까지 추적 |
| **CategoryItem** | 아이템을 폴더 아래에 분류하는 링크 | 소스를 재처리하지 않고 관련 메모리를 탐색 |
| **Embedding** | 폴더, 파일, 소스를 아우르는 벡터 인덱스 | 낮은 지연으로 관련 컨텍스트를 검색 |

`memorize()` 출력 예시:

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

그런 다음 에이전트는 `retrieve()`를 호출하여 범위가 지정되고 순위가 매겨진 컨텍스트 페이로드를 얻을 수 있습니다:

```python
context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What context matters for this launch task?"}}],
    where={"user_id": "123"},
)
```

---

## ⭐️ 저장소에 스타 누르기

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />

memU가 유용하거나 흥미롭다고 느끼셨다면, GitHub 스타 ⭐️ 를 눌러 주시면 정말 감사하겠습니다.

---

## ✨ 핵심 기능

| 기능 | 설명 |
|------------|-------------|
| 🗂️ **멀티모달 수집** | 대화, 문서, 이미지, 비디오, 오디오, URL, 로그, 로컬 파일을 메모리에 기록 |
| 📁 **메모리 파일 시스템** | 폴더(카테고리), 파일(아이템), 소스 산출물, 링크, 요약, 임베딩을 영속화 |
| 🧠 **타입 지정 메모리 추출** | 원본 소스에서 profile, event, knowledge, behavior, skill, tool 메모리를 추출 |
| 🧭 **자기 조직화 폴더** | 수동 태깅 없이 카테고리, 링크, 요약, 임베딩을 자동 구축 |
| 🤖 **에이전트 친화적 검색** | 어떤 에이전트 워크플로에도 주입할 수 있는, 범위 지정되고 순위가 매겨진 컨텍스트를 읽기 |
| 🧱 **플러그형 스토리지** | 동일한 리포지토리 계약으로 in-memory, SQLite, Postgres 백엔드 사용 |
| 🔀 **프로파일 기반 LLM 라우팅** | 설정 가능한 LLM 프로파일로 채팅, 임베딩, 비전, 전사 작업을 라우팅 |

---

## 🎯 활용 사례

### 1. **대화 메모리**
*채팅 로그를 사용자 선호, 목표, 사건, 관계 컨텍스트로 전환.*

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

### 2. **코딩 에이전트를 위한 워크스페이스 컨텍스트**
*문서, PR 메모, 로그, 설계 결정을 재사용 가능한 프로젝트 메모리로 전환.*

```python
await service.memorize(resource_url="docs/architecture.md", modality="document")
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "How should I structure this module?"}}],
)
```

### 3. **멀티모달 지식 계층**
*문서, 스크린샷, 이미지, 비디오, 음성 메모에서 검색 가능한 사실을 추출.*

```python
await service.memorize(resource_url="examples/resources/docs/doc1.txt", modality="document")
await service.memorize(resource_url="examples/resources/images/image1.png", modality="image")
# Audio is supported for your own .mp3/.wav/.m4a files.
await service.memorize(resource_url="meeting-audio.mp3", modality="audio")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What matters for the next research plan?"}}],
)
```

### 4. **도구와 에이전트 학습**
*실행 트레이스를 도구 메모리로 전환하여, 미래의 에이전트에게 언제 도구를 써야 하고 어떤 실수를 피해야 하는지 알려줍니다.*

```python
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "Which tools worked for config editing?"}}],
)
```

---

## 🗂️ 아키텍처

메모리 파일 시스템은 탐색할 만큼 계층적이면서 직접 검색할 만큼 구조화되어 있습니다:

<img width="100%" alt="structure" src="../assets/structure.png" />

| 계층 | 주요 역할 | 검색 역할 |
|-------|--------------|----------------|
| **Category(폴더)** | 주제 수준 요약을 유지 | 폭넓은 질의를 위해 간결한 컨텍스트를 조립 |
| **Item(파일)** | 타입 지정 원자 메모리를 저장 | 정확한 사실, 사건, 선호, 스킬, 도구 패턴을 로드 |
| **Resource(소스)** | 소스 산출물과 캡션을 보존 | 아이템/카테고리 요약으로 부족할 때 원본 컨텍스트를 회수 |

`MemoryService`, 워크플로 파이프라인, 스토리지 백엔드, LLM 라우팅의 런타임 관점은 [docs/architecture.md](../docs/architecture.md)를 참고하세요.

---

## 🚀 빠른 시작

### 옵션 1: 클라우드 버전

👉 **[memu.so](https://memu.so)** — 관리형 수집, 구조화 메모리, 검색을 제공하는 호스팅 API

엔터프라이즈 배포: **info@nevamind.ai**

#### Cloud API (v3)

| Base URL | `https://api.memu.so` |
|----------|----------------------|
| Auth | `Authorization: Bearer <token>` |

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v3/memory/memorize` | 원본 데이터를 수집하고 구조화 메모리를 구축 |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | 처리 상태 확인 |
| `POST` | `/api/v3/memory/categories` | 자동 생성된 카테고리 나열 |
| `POST` | `/api/v3/memory/retrieve` | 에이전트 컨텍스트를 위해 메모리 질의 |

📚 **[전체 API 문서](https://memu.pro/docs#cloud-version)**

---

### 옵션 2: 셀프 호스팅

#### 설치

이 저장소의 클론에서:

```bash
uv sync
# 또는, 전체 개발 환경 설정:
make install
```

게시된 패키지를 설치하려면:

```bash
pip install memu-py
```

> **요구 사항**: Python 3.13+. 기본 예제는 OpenAI를 사용하므로 `OPENAI_API_KEY`를 설정하거나 `llm_profiles`로 다른 제공자를 전달하세요.

**인메모리 스모크 스크립트 실행:**
```bash
export OPENAI_API_KEY=your_key
cd tests
uv run python test_inmemory.py
```

**PostgreSQL + pgvector로 실행:**
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

### 사용자 지정 LLM 및 임베딩 제공자

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

### OpenRouter 연동

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

## 📖 핵심 API

### `memorize()` — 원본 데이터 구조화

<img width="100%" alt="memorize" src="../assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",    # 로컬 파일 경로 또는 HTTP URL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"},            # 선택: 사용자 또는 에이전트로 범위 한정
)
# 처리 완료 후 반환:
# { "resource": {...}, "items": [...], "categories": [...], "relations": [...] }
```

- 원본 입력을 타입 지정 메모리 아이템으로 변환
- 수동 태깅 없이 아이템을 분류하고 임베딩
- 소스 리소스와 아이템–카테고리 관계를 보존

---

### `retrieve()` — 에이전트 컨텍스트 로드

<img width="100%" alt="retrieve" src="../assets/retrieve.png" />

```python
# 검색 전략은 retrieve_config로 서비스에 한 번만 설정합니다:
#   MemoryService(retrieve_config={"method": "rag"})   # 벡터 우선 회수
#   MemoryService(retrieve_config={"method": "llm"})   # LLM 순위 회수
result = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What are their preferences?"}}],
    where={"user_id": "123"},   # 범위 필터
)
# 반환:
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

| `retrieve_config.method` | 동작 | 비용 | 적합한 용도 |
|--------------------------|----------|------|----------|
| `rag` | 벡터 우선의 카테고리/아이템/리소스 회수. 선택적 LLM 라우팅과 충분성 검사가 기본 활성화 | `route_intention`과 `sufficiency_check`를 비활성화하지 않는 한, 임베딩에 더해 LLM 호출 | 추론을 제어 가능한 빠른 범위 회수 |
| `llm` | LLM이 순위를 매기는 카테고리/아이템/리소스 회수 | 각 계층에서 LLM 순위 매김 | 더 깊은 의미적 순위 매김 |

---

## 💡 예시 워크플로

### 항상 학습하는 어시스턴트
```bash
export OPENAI_API_KEY=your_key
uv run python examples/example_1_conversation_memory.py
```
선호를 자동으로 추출하고, 관계 모델을 구축하며, 이후 대화에서 관련 컨텍스트를 떠올립니다.

### 자기 개선하는 에이전트
```bash
uv run python examples/example_2_skill_extraction.py
```
에이전트의 행동을 모니터링하고, 성공과 실패의 패턴을 식별하며, 경험으로부터 스킬 가이드를 자동 생성합니다.

### 멀티모달 컨텍스트 빌더
```bash
uv run python examples/example_3_multimodal_memory.py
```
텍스트, 이미지, 문서를 자동으로 상호 참조하여 통합된 메모리 계층으로 묶습니다.

---

## 📊 성능

memU는 Locomo 벤치마크의 모든 추론 작업에서 **평균 92.09% 정확도**를 달성합니다.

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

자세한 결과 보기: [memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 에코시스템

| 저장소 | 설명 |
|------------|-------------|
| **[memU](https://github.com/NevaMind-AI/memU)** | 핵심 메모리 파일 시스템 — 수집, 추출, 검색 |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | 실시간 동기화와 webhook 트리거를 갖춘 백엔드 |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | 메모리를 탐색하고 모니터링하는 비주얼 대시보드 |

**빠른 링크:**
- 🚀 [MemU Cloud 사용해 보기](https://app.memu.so/quick-start)
- 📚 [API 문서](https://memu.pro/docs)
- 💬 [Discord 커뮤니티](https://discord.com/invite/hQZntfGsbJ)

---

## 🤝 파트너

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

## 🤝 기여하기

```bash
# 포크하고 클론
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# 개발 의존성 설치
make install

# 제출 전 품질 검사 실행
make check
```

자세한 가이드라인은 [CONTRIBUTING.md](../CONTRIBUTING.md)를 참고하세요.

**필수 조건:** Python 3.13+, [uv](https://github.com/astral-sh/uv), Git

---

## 📄 라이선스

[Apache License 2.0](../LICENSE.txt)

---

## 🌍 커뮤니티

- **GitHub Issues**: [버그 신고 및 기능 요청](https://github.com/NevaMind-AI/memU/issues)
- **Discord**: [커뮤니티 참여](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**: [@memU_ai 팔로우](https://x.com/memU_ai)
- **연락처**: info@nevamind.ai

---

<div align="center">

⭐ **GitHub에서 스타를** 눌러 새 릴리스 알림을 받으세요!

</div>
