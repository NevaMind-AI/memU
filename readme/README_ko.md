![MemU Banner](../assets/banner.png)

<div align="center">

# memU

### AI 에이전트를 위한 상시 가동 프로액티브 메모리

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](README_en.md) | [中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md)**

</div>

---

memU는 **24/7 프로액티브 에이전트**를 위해 구축된 메모리 프레임워크입니다.
장시간 실행을 위해 설계되었으며, 에이전트를 항상 온라인으로 유지하는 **LLM 토큰 비용을 크게 절감**하여 상시 가동되고 진화하는 에이전트를 프로덕션 시스템에서 실용적으로 만듭니다.
memU는 **사용자 의도를 지속적으로 캡처하고 이해**합니다. 명령이 없어도 에이전트는 당신이 무엇을 하려는지 파악하고 스스로 행동합니다.

---

## 🤖 [OpenClaw (Moltbot, Clawdbot) Alternative](https://memu.bot)

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/memUbot.png" />

- **Download-and-use and simple** to get started.
- Builds long-term memory to **understand user intent** and act proactively.
- **Cuts LLM token cost** with smaller context.

Try now: [memU bot](https://memu.bot)

---

## 🗃️ 메모리는 파일 시스템, 파일 시스템은 메모리

memU는 **메모리를 파일 시스템처럼** 다룹니다—구조화되고, 계층적이며, 즉시 접근 가능합니다.

| 파일 시스템 | memU 메모리 |
|------------|------------|
| 📁 폴더 | 🏷️ 카테고리 (자동 정리된 주제) |
| 📄 파일 | 🧠 메모리 아이템 (추출된 사실, 선호도, 스킬) |
| 🔗 심볼릭 링크 | 🔄 교차 참조 (연관된 메모리 연결) |
| 📂 마운트 포인트 | 📥 리소스 (대화, 문서, 이미지) |

**왜 중요한가:**
- **디렉토리를 탐색하듯 메모리를 탐색**—넓은 카테고리에서 구체적인 사실로 드릴다운
- **새로운 지식을 즉시 마운트**—대화와 문서가 쿼리 가능한 메모리로 변환
- **모든 것을 교차 연결**—메모리가 서로를 참조하여 연결된 지식 그래프 구축
- **영구적이고 이식 가능**—파일처럼 메모리를 내보내기, 백업, 전송

```
memory/
├── preferences/
│   ├── communication_style.md
│   └── topic_interests.md
├── relationships/
│   ├── contacts/
│   └── interaction_history/
├── knowledge/
│   ├── domain_expertise/
│   └── learned_skills/
└── context/
    ├── recent_conversations/
    └── pending_tasks/
```

파일 시스템이 원시 바이트를 정리된 데이터로 변환하듯, memU는 원시 상호작용을 **구조화되고, 검색 가능하며, 프로액티브한 인텔리전스**로 변환합니다.

---

## ⭐️ 리포지토리에 스타를

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />
MemU가 유용하거나 흥미롭다면, GitHub Star ⭐️를 눌러주시면 큰 힘이 됩니다.

---


## ✨ 핵심 기능

| 기능 | 설명 |
|------|------|
| 🤖 **24/7 프로액티브 에이전트** | 백그라운드에서 지속적으로 작동하는 상시 가동 메모리 에이전트—절대 잠들지 않고, 절대 잊지 않습니다 |
| 🎯 **사용자 의도 캡처** | 세션 간에 사용자의 목표, 선호도, 컨텍스트를 자동으로 이해하고 기억 |
| 💰 **비용 효율적** | 인사이트를 캐싱하고 중복 LLM 호출을 방지하여 장기 실행 토큰 비용 절감 |
---

## 🔄 프로액티브 메모리 작동 방식

```bash

cd examples/proactive
python proactive.py

```

---

### Proactive Memory Lifecycle
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         USER QUERY                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
                 │                                                           │
                 ▼                                                           ▼
┌────────────────────────────────────────┐         ┌────────────────────────────────────────────────┐
│         🤖 MAIN AGENT                  │         │              🧠 MEMU BOT                       │
│                                        │         │                                                │
│  Handle user queries & execute tasks   │  ◄───►  │  Monitor, memorize & proactive intelligence   │
├────────────────────────────────────────┤         ├────────────────────────────────────────────────┤
│                                        │         │                                                │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  1. RECEIVE USER INPUT           │  │         │  │  1. MONITOR INPUT/OUTPUT                 │  │
│  │     Parse query, understand      │  │   ───►  │  │     Observe agent interactions           │  │
│  │     context and intent           │  │         │  │     Track conversation flow              │  │
│  └──────────────────────────────────┘  │         │  └──────────────────────────────────────────┘  │
│                 │                      │         │                    │                           │
│                 ▼                      │         │                    ▼                           │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  2. PLAN & EXECUTE               │  │         │  │  2. MEMORIZE & EXTRACT                   │  │
│  │     Break down tasks             │  │   ◄───  │  │     Store insights, facts, preferences   │  │
│  │     Call tools, retrieve data    │  │  inject │  │     Extract skills & knowledge           │  │
│  │     Generate responses           │  │  memory │  │     Update user profile                  │  │
│  └──────────────────────────────────┘  │         │  └──────────────────────────────────────────┘  │
│                 │                      │         │                    │                           │
│                 ▼                      │         │                    ▼                           │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  3. RESPOND TO USER              │  │         │  │  3. PREDICT USER INTENT                  │  │
│  │     Deliver answer/result        │  │   ───►  │  │     Anticipate next steps                │  │
│  │     Continue conversation        │  │         │  │     Identify upcoming needs              │  │
│  └──────────────────────────────────┘  │         │  └──────────────────────────────────────────┘  │
│                 │                      │         │                    │                           │
│                 ▼                      │         │                    ▼                           │
│  ┌──────────────────────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  4. LOOP                         │  │         │  │  4. RUN PROACTIVE TASKS                  │  │
│  │     Wait for next user input     │  │   ◄───  │  │     Pre-fetch relevant context           │  │
│  │     or proactive suggestions     │  │  suggest│  │     Prepare recommendations              │  │
│  └──────────────────────────────────┘  │         │  │     Update todolist autonomously         │  │
│                                        │         │  └──────────────────────────────────────────┘  │
└────────────────────────────────────────┘         └────────────────────────────────────────────────┘
                 │                                                           │
                 └───────────────────────────┬───────────────────────────────┘
                                             ▼
                              ┌──────────────────────────────┐
                              │     CONTINUOUS SYNC LOOP     │
                              │  Agent ◄──► MemU Bot ◄──► DB │
                              └──────────────────────────────┘
```

---

## 🎯 프로액티브 사용 사례

### 1. **정보 추천**
*에이전트가 관심사를 모니터링하고 관련 콘텐츠를 프로액티브하게 표시*
```python
# 사용자가 AI 주제를 연구하고 있음
MemU 추적: 읽기 기록, 저장한 기사, 검색 쿼리

# 새 콘텐츠가 도착했을 때:
에이전트: "검색 시스템에 대한 최근 연구와 일치하는 RAG 최적화에
          대한 3개의 새 논문을 찾았습니다. 이전에 인용한 저자
          (Dr. Chen)가 어제 발표했습니다."

# 프로액티브 행동:
- 브라우징 패턴에서 주제 선호도 학습
- 저자/소스 신뢰도 선호도 추적
- 참여 기록을 기반으로 노이즈 필터링
- 최적의 주의를 끌 수 있는 타이밍에 추천
```

### 2. **이메일 관리**
*에이전트가 커뮤니케이션 패턴을 학습하고 일상적인 통신 처리*
```python
# MemU가 시간에 따라 이메일 패턴을 관찰:
- 일반적인 시나리오에 대한 응답 템플릿
- 우선 연락처와 긴급 키워드
- 일정 선호도와 가용 시간
- 글쓰기 스타일과 톤 변화

# 프로액티브 이메일 지원:
에이전트: "12개의 새 이메일이 있습니다. 3개의 일반 요청에 대한
          답장을 작성했고, 우선 연락처로부터의 2개 긴급 항목에
          플래그를 달았습니다. John이 언급한 충돌에 따라
          내일 회의를 재조정할까요?"

# 자율적 작업:
✓ 컨텍스트 인식 답장 초안 작성
✓ 받은 편지함 분류 및 우선순위 지정
✓ 일정 충돌 감지
✓ 주요 결정이 포함된 긴 스레드 요약
```

### 3. **트레이딩 & 금융 모니터링**
*에이전트가 시장 컨텍스트와 사용자 투자 행동 추적*
```python
# MemU가 트레이딩 선호도 학습:
- 과거 결정에서의 위험 허용 범위
- 선호 섹터 및 자산 클래스
- 시장 이벤트에 대한 반응 패턴
- 포트폴리오 리밸런싱 트리거

# 프로액티브 알림:
에이전트: "NVDA가 시간 외 거래에서 5% 하락했습니다. 과거 행동에
          기반하여, 일반적으로 3% 이상 기술주 하락 시 매수합니다.
          현재 배분으로 70/30 주식-채권 목표를 유지하면서
          $2,000 추가 노출이 가능합니다."

# 지속적 모니터링:
- 사용자 정의 임계값과 연결된 가격 알림 추적
- 뉴스 이벤트와 포트폴리오 영향 연관
- 실행된 추천과 무시된 추천에서 학습
- 세금 손실 수확 기회 예측
```


...

---

## 🗂️ 계층적 메모리 아키텍처

MemU의 3계층 시스템은 **반응적 쿼리**와 **프로액티브 컨텍스트 로딩**을 모두 지원합니다:

<img width="100%" alt="structure" src="../assets/structure.png" />

| 계층 | 반응적 사용 | 프로액티브 사용 |
|------|-----------|----------------|
| **리소스** | 원본 데이터에 직접 액세스 | 새 패턴의 백그라운드 모니터링 |
| **아이템** | 타겟팅된 팩트 검색 | 진행 중인 상호작용에서 실시간 추출 |
| **카테고리** | 요약 수준 개요 | 예측을 위한 자동 컨텍스트 조합 |

**프로액티브 이점:**
- **자동 분류**: 새로운 메모리가 주제로 자체 조직화
- **패턴 감지**: 시스템이 반복되는 테마를 식별
- **컨텍스트 예측**: 다음에 필요한 정보를 예측

---

## 🚀 빠른 시작

### 옵션 1: 클라우드 버전

프로액티브 메모리를 즉시 경험하세요:

👉 **[memu.so](https://memu.so)** - 7×24 지속 학습을 제공하는 호스팅 서비스

사용자 정의 프로액티브 워크플로우를 포함한 엔터프라이즈 배포는 **info@nevamind.ai**로 문의하세요

#### 클라우드 API (v3)

| 기본 URL | `https://api.memu.so` |
|---------|----------------------|
| 인증 | `Authorization: Bearer YOUR_API_KEY` |

| 메소드 | 엔드포인트 | 설명 |
|-------|----------|------|
| `POST` | `/api/v3/memory/memorize` | 지속 학습 작업 등록 |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | 실시간 처리 상태 확인 |
| `POST` | `/api/v3/memory/categories` | 자동 생성된 카테고리 목록 |
| `POST` | `/api/v3/memory/retrieve` | 메모리 쿼리 (프로액티브 컨텍스트 로딩 지원) |

📚 **[전체 API 문서](https://memu.pro/docs#cloud-version)**

---

### 옵션 2: 셀프 호스팅

#### 설치
```bash
pip install -e .
```

#### 기본 예제

> **요구사항**: Python 3.13+ 및 OpenAI API 키

**지속 학습 테스트** (인메모리):
```bash
export OPENAI_API_KEY=your_api_key
cd tests
python test_inmemory.py
```

**영구 저장소로 테스트** (PostgreSQL):
```bash
# pgvector가 포함된 PostgreSQL 시작
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 지속 학습 테스트 실행
export OPENAI_API_KEY=your_api_key
cd tests
python test_postgres.py
```

두 예제 모두 **프로액티브 메모리 워크플로우**를 보여줍니다:
1. **지속적 수집**: 여러 파일을 순차적으로 처리
2. **자동 추출**: 즉각적인 메모리 생성
3. **프로액티브 검색**: 컨텍스트 인식 메모리 표시

구현 세부사항은 [`tests/test_inmemory.py`](../tests/test_inmemory.py)와 [`tests/test_postgres.py`](../tests/test_postgres.py)를 참조하세요.

---

### 커스텀 LLM 및 임베딩 제공자

MemU는 OpenAI 외에도 커스텀 LLM 및 임베딩 제공자를 지원합니다. `llm_profiles`로 구성:
```python
from memu import MemUService

service = MemUService(
    llm_profiles={
        # LLM 작업용 기본 프로필
        "default": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "your_api_key",
            "chat_model": "qwen3-max",
            "client_backend": "sdk"  # "sdk" 또는 "http"
        },
        # 임베딩용 별도 프로필
        "embedding": {
            "base_url": "https://api.voyageai.com/v1",
            "api_key": "your_voyage_api_key",
            "embed_model": "voyage-3.5-lite"
        }
    },
    # ... 기타 구성
)
```

---

### OpenRouter 통합

MemU는 [OpenRouter](https://openrouter.ai)를 모델 제공자로 지원하여 단일 API를 통해 여러 LLM 제공자에 액세스할 수 있습니다.

#### 구성
```python
from memu import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openrouter",
            "client_backend": "httpx",
            "base_url": "https://openrouter.ai",
            "api_key": "your_openrouter_api_key",
            "chat_model": "anthropic/claude-3.5-sonnet",  # 모든 OpenRouter 모델
            "embed_model": "openai/text-embedding-3-small",  # 임베딩 모델
        },
    },
    database_config={
        "metadata_store": {"provider": "inmemory"},
    },
)
```

#### 환경 변수

| 변수 | 설명 |
|------|------|
| `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys)에서 받은 OpenRouter API 키 |

#### 지원 기능

| 기능 | 상태 | 참고 |
|------|------|------|
| 채팅 완성 | 지원됨 | 모든 OpenRouter 채팅 모델과 작동 |
| 임베딩 | 지원됨 | OpenRouter를 통해 OpenAI 임베딩 모델 사용 |
| 비전 | 지원됨 | 비전 지원 모델 사용 (예: `openai/gpt-4o`) |

#### OpenRouter 테스트 실행
```bash
export OPENROUTER_API_KEY=your_api_key

# 전체 워크플로우 테스트 (메모라이즈 + 검색)
python tests/test_openrouter.py

# 임베딩 특화 테스트
python tests/test_openrouter_embedding.py

# 비전 특화 테스트
python tests/test_openrouter_vision.py
```

완전한 작동 예제는 [`examples/example_4_openrouter_memory.py`](../examples/example_4_openrouter_memory.py)를 참조하세요.

---

## 📖 핵심 API

### `memorize()` - 지속 학습 파이프라인

입력을 실시간으로 처리하고 메모리를 즉시 업데이트:

<img width="100%" alt="memorize" src="../assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",  # 파일 경로 또는 URL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"}             # 선택: 사용자로 범위 지정
)

# 추출된 메모리를 즉시 반환:
{
    "resource": {...},      # 저장된 리소스 메타데이터
    "items": [...],         # 추출된 메모리 아이템 (즉시 사용 가능)
    "categories": [...]     # 자동 업데이트된 카테고리 구조
}
```

**프로액티브 기능:**
- 지연 없는 처리—메모리 즉시 사용 가능
- 수동 태그 지정 없는 자동 분류
- 패턴 감지를 위한 기존 메모리와의 상호 참조

### `retrieve()` - 이중 모드 인텔리전스

MemU는 **프로액티브 컨텍스트 로딩**과 **반응적 쿼리**를 모두 지원:

<img width="100%" alt="retrieve" src="../assets/retrieve.png" />

#### RAG 기반 검색 (`method="rag"`)

임베딩을 사용한 빠른 **프로액티브 컨텍스트 조합**:

- ✅ **즉각적 컨텍스트**: 1초 미만의 메모리 표시
- ✅ **백그라운드 모니터링**: LLM 비용 없이 지속적으로 실행 가능
- ✅ **유사도 점수**: 가장 관련성 높은 메모리를 자동으로 식별

#### LLM 기반 검색 (`method="llm"`)

복잡한 컨텍스트를 위한 심층 **예측적 추론**:

- ✅ **의도 예측**: LLM이 사용자가 묻기 전에 필요를 추론
- ✅ **쿼리 진화**: 컨텍스트 발전에 따라 검색 자동 개선
- ✅ **조기 종료**: 충분한 컨텍스트가 수집되면 중지

#### 비교

| 측면 | RAG (빠른 컨텍스트) | LLM (심층 추론) |
|------|-------------------|----------------|
| **속도** | ⚡ 밀리초 | 🐢 초 |
| **비용** | 💰 임베딩만 | 💰💰 LLM 추론 |
| **프로액티브 사용** | 지속적 모니터링 | 트리거된 컨텍스트 로딩 |
| **최적 용도** | 실시간 제안 | 복잡한 예측 |

#### 사용법
```python
# 컨텍스트 히스토리를 포함한 프로액티브 검색
result = await service.retrieve(
    queries=[
        {"role": "user", "content": {"text": "그들의 선호도가 무엇입니까?"}},
        {"role": "user", "content": {"text": "업무 습관에 대해 알려주세요"}}
    ],
    where={"user_id": "123"},  # 선택: 범위 필터
    method="rag"  # 또는 "llm"으로 더 깊은 추론
)

# 컨텍스트 인식 결과 반환:
{
    "categories": [...],     # 관련 주제 영역 (자동 우선순위)
    "items": [...],          # 구체적인 메모리 팩트
    "resources": [...],      # 추적 가능한 원본 소스
    "next_step_query": "..." # 예측된 후속 컨텍스트
}
```

**프로액티브 필터링**: `where`를 사용하여 지속적 모니터링 범위 지정:
- `where={"user_id": "123"}` - 사용자별 컨텍스트
- `where={"agent_id__in": ["1", "2"]}` - 다중 에이전트 조정
- `where` 생략으로 전역 컨텍스트 인식

> 📚 **전체 API 문서**는 [SERVICE_API.md](../docs/SERVICE_API.md) 참조 - 프로액티브 워크플로우 패턴, 파이프라인 구성, 실시간 업데이트 처리 포함.

---

## 💡 프로액티브 시나리오

### 예제 1: 항상 학습하는 어시스턴트

명시적인 메모리 명령 없이 모든 상호작용에서 지속적으로 학습:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_1_conversation_memory.py
```

**프로액티브 행동:**
- 일상적인 언급에서 선호도를 자동으로 추출
- 상호작용 패턴에서 관계 모델 구축
- 향후 대화에서 관련 컨텍스트 표시
- 학습된 선호도에 따라 커뮤니케이션 스타일 적응

**최적 용도:** 개인 AI 어시스턴트, 기억하는 고객 지원, 소셜 챗봇

---

### 예제 2: 자기 개선 에이전트

실행 로그에서 학습하고 최적화를 프로액티브하게 제안:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_2_skill_extraction.py
```

**프로액티브 행동:**
- 에이전트 행동과 결과를 지속적으로 모니터링
- 성공과 실패의 패턴 식별
- 경험에서 스킬 가이드 자동 생성
- 유사한 미래 작업에 대한 전략을 프로액티브하게 제안

**최적 용도:** DevOps 자동화, 에이전트 자기 개선, 지식 캡처

---

### 예제 3: 멀티모달 컨텍스트 빌더

포괄적인 컨텍스트를 위해 다양한 입력 유형의 메모리 통합:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_3_multimodal_memory.py
```

**프로액티브 행동:**
- 텍스트, 이미지, 문서를 자동으로 상호 참조
- 모달리티 전반에 걸쳐 통합된 이해 구축
- 관련 주제 논의 시 시각적 컨텍스트 표시
- 여러 소스를 결합하여 정보 필요 예측

**최적 용도:** 문서 시스템, 학습 플랫폼, 연구 어시스턴트

---

## 📊 성능

MemU는 모든 추론 작업에서 Locomo 벤치마크에서 **92.09% 평균 정확도**를 달성하여 신뢰할 수 있는 프로액티브 메모리 작업을 입증합니다.

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

상세 실험 데이터 보기: [memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 에코시스템

| 리포지토리 | 설명 | 프로액티브 기능 |
|-----------|------|----------------|
| **[memU](https://github.com/NevaMind-AI/memU)** | 핵심 프로액티브 메모리 엔진 | 7×24 학습 파이프라인, 자동 분류 |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | 지속 동기화가 포함된 백엔드 | 실시간 메모리 업데이트, 웹훅 트리거 |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | 시각적 메모리 대시보드 | 라이브 메모리 진화 모니터링 |

**빠른 링크:**
- 🚀 [MemU Cloud 체험](https://app.memu.so/quick-start)
- 📚 [API 문서](https://memu.pro/docs)
- 💬 [Discord 커뮤니티](https://discord.gg/memu)

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

</div>

---

## 🤝 기여 방법

커뮤니티의 기여를 환영합니다! 버그 수정, 기능 추가, 문서 개선 등 어떤 도움이든 감사합니다.

### 시작하기

MemU에 기여하려면 개발 환경을 설정해야 합니다:

#### 사전 요구사항
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (Python 패키지 관리자)
- Git

#### 개발 환경 설정
```bash
# 1. 리포지토리 포크 및 클론
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# 2. 개발 의존성 설치
make install
```

`make install` 명령은:
- `uv`를 사용하여 가상 환경 생성
- 모든 프로젝트 의존성 설치
- 코드 품질 검사를 위한 pre-commit 훅 설정

#### 품질 검사 실행

기여를 제출하기 전에 코드가 모든 품질 검사를 통과하는지 확인하세요:
```bash
make check
```

`make check` 명령은:
- **잠금 파일 검증**: `pyproject.toml` 일관성 확인
- **Pre-commit 훅**: Ruff로 코드 린트, Black으로 포맷
- **타입 검사**: 정적 타입 분석을 위한 `mypy` 실행
- **의존성 분석**: `deptry`로 오래된 의존성 찾기

### 기여 가이드라인

상세한 기여 가이드라인, 코드 표준 및 개발 관행은 [CONTRIBUTING.md](../CONTRIBUTING.md)를 참조하세요.

**빠른 팁:**
- 각 기능 또는 버그 수정을 위한 새 브랜치 생성
- 명확한 커밋 메시지 작성
- 새 기능에 대한 테스트 추가
- 필요에 따라 문서 업데이트
- 푸시 전 `make check` 실행

---

## 📄 라이선스

[Apache License 2.0](../LICENSE.txt)

---

## 🌍 커뮤니티

- **GitHub Issues**: [버그 보고 및 기능 요청](https://github.com/NevaMind-AI/memU/issues)
- **Discord**: [커뮤니티 참여](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**: [@memU_ai 팔로우](https://x.com/memU_ai)
- **연락처**: info@nevamind.ai

---

<div align="center">

⭐ **GitHub에서 스타를 눌러** 새 릴리스 알림을 받으세요!

</div>
