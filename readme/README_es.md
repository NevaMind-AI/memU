![MemU Banner](../assets/banner.png)

<div align="center">

# memU

### El sistema de archivos como memoria, la memoria moldea al agente

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.com/invite/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](README_en.md) | [中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md)**

</div>

---

memU es un **sistema de archivos de memoria** para agentes de IA.

En lugar de aplastar todo lo que un agente aprende en un único prompt gigante o en un blob vectorial opaco, memU organiza la memoria como organizarías una computadora: como un árbol navegable de archivos Markdown legibles por humanos.

- **`MEMORY.md`**: la memoria viva del agente: quién es el usuario, sus preferencias, objetivos y los eventos extraídos de cada fuente
- **`SKILL.md`**: habilidades y patrones de herramientas aprendidos: qué funcionó, qué evitar y cómo repetir tareas recurrentes
- **`INDEX.md`**: la tabla de contenidos: un mapa navegable de todos los archivos de memoria, para que el agente sepa dónde mirar antes de leer
- **El agente lee y escribe estos archivos**: usa `memorize()` para escribir nuevas fuentes en ellos y `retrieve()` para leer, bajo demanda, solo las secciones que importan

```txt
memory/
├── INDEX.md              ← mapa de todo: categorías, archivos y resúmenes
├── MEMORY.md             ← perfil, preferencias, objetivos y eventos clave
└── skill/
    ├── {skill_name}/
    │   └── SKILL.md       ← una habilidad o patrón de herramienta aprendido
    └── {another_skill}/
        └── SKILL.md
```

**El sistema de archivos como memoria**: una superficie jerárquica y navegable donde cada memoria puede rastrearse hasta su fuente.
**La memoria moldea al agente**: como esa superficie es estructurada y autoorganizada, deja de ser almacenamiento pasivo y se convierte en la capa que moldea cómo piensa y actúa el agente.

---

## 🔄 Cómo funciona

Piénsalo como dos operaciones de sistema de archivos: **escribir** fuentes en bruto en una memoria organizada y **leer** los archivos correctos de vuelta hacia el agente.

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

**Escribir en el sistema de archivos (`memorize`)**

1. **Ingerir (Ingest)**: almacena cada fuente como un `Resource` (el archivo en bruto) con su modalidad y ubicación de origen
2. **Preprocesar (Preprocess)**: analiza texto, genera descripciones de imágenes/video, transcribe audio y normaliza las entradas
3. **Extraer (Extract)**: convierte el contenido en bruto en `MemoryItem`s tipados (los archivos): memorias de tipo profile, event, knowledge, behavior, skill o tool
4. **Organizar (Organize)**: clasifica los elementos en carpetas `MemoryCategory`, los enlaza entre sí, los vectoriza y los resume en un árbol navegable
5. **Persistir (Persist)**: escribe registros, relaciones, embeddings y resúmenes de carpeta a través del backend configurado

**Leer del sistema de archivos (`retrieve`)**

6. **Recuperar (Retrieve)**: navega por las carpetas y devuelve solo los archivos relevantes para el usuario, agente, sesión o tarea actuales

---

## 🗂️ El sistema de archivos de memoria

La salida principal de memU es un árbol de memoria navegable —carpetas, archivos y los artefactos de origen detrás de ellos— persistido mediante contratos de repositorio y devuelto como diccionarios desde `memorize()` y `retrieve()`.

```txt
MemoryCategory                       ← carpeta: un tema con un resumen en evolución
├── name, description, summary
├── embedding
└── MemoryItem[]                     ← archivos: memorias atómicas y tipadas
    ├── memory_type: profile | event | knowledge | behavior | skill | tool
    ├── summary, extra, happened_at, embedding
    └── Resource                     ← fuente: el archivo en bruto del que proviene esta memoria
        └── url, modality, local_path, caption, embedding
```

| Registro | Rol en el sistema de archivos | Usado para |
|--------|------------------|---------|
| `MemoryCategory` | **Carpeta**: agrupa memorias relacionadas y mantiene un resumen a nivel de tema | Cargar contexto compacto para consultas amplias |
| `MemoryItem` | **Archivo**: memoria atómica tipada con un resumen y metadatos opcionales | Inyectar hechos, preferencias, eventos, habilidades y patrones de herramientas precisos |
| `Resource` | **Artefacto de origen**: el archivo original detrás de una memoria, con descripción/texto | Rastrear el contexto hasta su origen |
| `CategoryItem` | **Enlace**: la arista que archiva un elemento bajo una carpeta | Navegar memorias relacionadas sin reprocesar la fuente |

Esto da a los agentes un sistema de archivos de memoria estable: ingieren las fuentes en bruto una sola vez y luego solicitan archivos delimitados y ordenados, en lugar de releer cada artefacto de origen.

---

## 🧩 Qué construye memU

Cada capa del sistema de archivos se almacena como un registro estructurado:

| Capa | Qué representa | Por qué la usan los agentes |
|-------|--------------------|-------------------|
| **MemoryCategory** | Carpeta autogenerada: un tema con un resumen en evolución | Cargar contexto de alto nivel antes de profundizar en detalles |
| **MemoryItem** | Un archivo: memoria estructurada atómica con un tipo y un resumen | Inyectar hechos, preferencias, eventos, habilidades y patrones de herramientas precisos |
| **Resource** | Artefacto de origen detrás de un archivo: conversación, documento, imagen, video, audio, URL o archivo | Rastrear la memoria hasta su origen |
| **CategoryItem** | El enlace que archiva un elemento bajo una carpeta | Navegar memorias relacionadas sin reprocesar la fuente |
| **Embedding** | Índice vectorial sobre carpetas, archivos y fuentes | Recuperar contexto relevante con baja latencia |

Ejemplo de salida de `memorize()`:

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

Luego un agente puede llamar a `retrieve()` para obtener una carga de contexto delimitada y ordenada por relevancia:

```python
context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What context matters for this launch task?"}}],
    where={"user_id": "123"},
)
```

---

## ⭐️ Dale una estrella al repositorio

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />

Si encuentras memU útil o interesante, una estrella ⭐️ en GitHub sería muy apreciada.

---

## ✨ Funciones principales

| Capacidad | Descripción |
|------------|-------------|
| 🗂️ **Ingesta multimodal** | Escribe conversaciones, documentos, imágenes, video, audio, URLs, registros y archivos locales en la memoria |
| 📁 **Sistema de archivos de memoria** | Persiste carpetas (categorías), archivos (elementos), artefactos de origen, enlaces, resúmenes y embeddings |
| 🧠 **Extracción de memoria tipada** | Extrae memorias profile, event, knowledge, behavior, skill y tool a partir de fuentes en bruto |
| 🧭 **Carpetas autoorganizadas** | Construye automáticamente categorías, enlaces, resúmenes y embeddings sin etiquetado manual |
| 🤖 **Recuperación lista para agentes** | Lee contexto delimitado y ordenado que puede inyectarse en cualquier flujo de trabajo de agente |
| 🧱 **Almacenamiento conectable** | Usa backends in-memory, SQLite o Postgres con los mismos contratos de repositorio |
| 🔀 **Enrutamiento de LLM basado en perfiles** | Enruta tareas de chat, embeddings, visión y transcripción a través de perfiles de LLM configurables |

---

## 🎯 Casos de uso

### 1. **Memoria de conversación**
*Convierte registros de chat en preferencias, objetivos, eventos y contexto de relación del usuario.*

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

### 2. **Contexto de espacio de trabajo para agentes de programación**
*Convierte documentos, notas de PR, registros y decisiones de diseño en memoria de proyecto reutilizable.*

```python
await service.memorize(resource_url="docs/architecture.md", modality="document")
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "How should I structure this module?"}}],
)
```

### 3. **Capa de conocimiento multimodal**
*Extrae hechos buscables de documentos, capturas de pantalla, imágenes, videos y notas de audio.*

```python
await service.memorize(resource_url="examples/resources/docs/doc1.txt", modality="document")
await service.memorize(resource_url="examples/resources/images/image1.png", modality="image")
# Audio is supported for your own .mp3/.wav/.m4a files.
await service.memorize(resource_url="meeting-audio.mp3", modality="audio")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What matters for the next research plan?"}}],
)
```

### 4. **Aprendizaje de herramientas y agentes**
*Convierte las trazas de ejecución en memorias de herramientas que indican a los agentes futuros cuándo usar una herramienta y qué errores evitar.*

```python
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "Which tools worked for config editing?"}}],
)
```

---

## 🗂️ Arquitectura

El sistema de archivos de memoria es lo bastante jerárquico para navegarlo y lo bastante estructurado para una recuperación directa:

<img width="100%" alt="structure" src="../assets/structure.png" />

| Capa | Rol principal | Rol en la recuperación |
|-------|--------------|----------------|
| **Category (carpeta)** | Mantener resúmenes a nivel de tema | Ensamblar contexto compacto para consultas amplias |
| **Item (archivo)** | Almacenar memorias atómicas tipadas | Cargar hechos, eventos, preferencias, habilidades y patrones de herramientas precisos |
| **Resource (fuente)** | Preservar artefactos de origen y descripciones | Recuperar el contexto original cuando los resúmenes de elemento/categoría no bastan |

Consulta [docs/architecture.md](../docs/architecture.md) para la vista en tiempo de ejecución de `MemoryService`, los pipelines de flujo de trabajo, los backends de almacenamiento y el enrutamiento de LLM.

---

## 🚀 Inicio rápido

### Opción 1: Versión en la nube

👉 **[memu.so](https://memu.so)**: API alojada para ingesta gestionada, memoria estructurada y recuperación

Para despliegue empresarial: **info@nevamind.ai**

#### Cloud API (v3)

| Base URL | `https://api.memu.so` |
|----------|----------------------|
| Auth | `Authorization: Bearer <token>` |

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v3/memory/memorize` | Ingiere datos en bruto y construye memoria estructurada |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | Consulta el estado del procesamiento |
| `POST` | `/api/v3/memory/categories` | Lista las categorías autogeneradas |
| `POST` | `/api/v3/memory/retrieve` | Consulta la memoria para obtener contexto del agente |

📚 **[Documentación completa de la API](https://memu.pro/docs#cloud-version)**

---

### Opción 2: Autoalojado

#### Instalación

Desde un clon de este repositorio:

```bash
uv sync
# o, para la configuración completa de desarrollo:
make install
```

Para instalar el paquete publicado en su lugar:

```bash
pip install memu-py
```

> **Requisitos**: Python 3.13+. Los ejemplos por defecto usan OpenAI, así que define `OPENAI_API_KEY` o pasa otro proveedor mediante `llm_profiles`.

**Ejecuta un script de prueba en memoria:**
```bash
export OPENAI_API_KEY=your_key
cd tests
uv run python test_inmemory.py
```

**Ejecuta con PostgreSQL + pgvector:**
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

### Proveedores personalizados de LLM y embeddings

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

### Integración con OpenRouter

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

## 📖 APIs principales

### `memorize()`: estructura datos en bruto

<img width="100%" alt="memorize" src="../assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",    # ruta de archivo local o URL HTTP
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"},            # opcional: delimitar a un usuario o agente
)
# Devuelve tras completar el procesamiento:
# { "resource": {...}, "items": [...], "categories": [...], "relations": [...] }
```

- Convierte la entrada en bruto en elementos de memoria tipados
- Categoriza y vectoriza los elementos sin etiquetado manual
- Preserva los recursos de origen y las relaciones elemento-categoría

---

### `retrieve()`: carga contexto del agente

<img width="100%" alt="retrieve" src="../assets/retrieve.png" />

```python
# La estrategia de recuperación se define una vez en el servicio mediante retrieve_config:
#   MemoryService(retrieve_config={"method": "rag"})   # recuperación con vectores primero
#   MemoryService(retrieve_config={"method": "llm"})   # recuperación ordenada por LLM
result = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What are their preferences?"}}],
    where={"user_id": "123"},   # filtro de alcance
)
# Devuelve:
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

| `retrieve_config.method` | Comportamiento | Coste | Mejor para |
|--------------------------|----------|------|----------|
| `rag` | Recuperación de categorías/elementos/recursos con vectores primero, con enrutamiento LLM y comprobaciones de suficiencia opcionales activadas por defecto | Embeddings más llamadas a LLM, salvo que se desactiven `route_intention` y `sufficiency_check` | Recuperación delimitada y rápida con razonamiento controlable |
| `llm` | Recuperación de categorías/elementos/recursos ordenada por LLM | Ordenación por LLM en cada nivel | Ordenación semántica más profunda |

---

## 💡 Flujos de trabajo de ejemplo

### Asistente que aprende siempre
```bash
export OPENAI_API_KEY=your_key
uv run python examples/example_1_conversation_memory.py
```
Extrae preferencias automáticamente, construye modelos de relación y hace aflorar contexto relevante en conversaciones futuras.

### Agente que se mejora a sí mismo
```bash
uv run python examples/example_2_skill_extraction.py
```
Supervisa las acciones del agente, identifica patrones en éxitos y fracasos, y autogenera guías de habilidades a partir de la experiencia.

### Constructor de contexto multimodal
```bash
uv run python examples/example_3_multimodal_memory.py
```
Cruza automáticamente texto, imágenes y documentos en una capa de memoria unificada.

---

## 📊 Rendimiento

memU alcanza un **92,09 % de precisión promedio** en el benchmark Locomo en todas las tareas de razonamiento.

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

Ver resultados detallados: [memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 Ecosistema

| Repositorio | Descripción |
|------------|-------------|
| **[memU](https://github.com/NevaMind-AI/memU)** | Sistema de archivos de memoria central: ingesta, extracción, recuperación |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | Backend con sincronización en tiempo real y disparadores webhook |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | Panel visual para explorar y monitorizar la memoria |

**Enlaces rápidos:**
- 🚀 [Prueba MemU Cloud](https://app.memu.so/quick-start)
- 📚 [Documentación de la API](https://memu.pro/docs)
- 💬 [Comunidad de Discord](https://discord.com/invite/hQZntfGsbJ)

---

## 🤝 Socios

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

## 🤝 Contribuir

```bash
# Haz fork y clona
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# Instala las dependencias de desarrollo
make install

# Ejecuta las comprobaciones de calidad antes de enviar
make check
```

Consulta [CONTRIBUTING.md](../CONTRIBUTING.md) para las pautas completas.

**Requisitos previos:** Python 3.13+, [uv](https://github.com/astral-sh/uv), Git

---

## 📄 Licencia

[Apache License 2.0](../LICENSE.txt)

---

## 🌍 Comunidad

- **GitHub Issues**: [Reporta errores y solicita funciones](https://github.com/NevaMind-AI/memU/issues)
- **Discord**: [Únete a la comunidad](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**: [Sigue a @memU_ai](https://x.com/memU_ai)
- **Contacto**: info@nevamind.ai

---

<div align="center">

⭐ **Danos una estrella en GitHub** para recibir notificaciones sobre nuevas versiones.

</div>
