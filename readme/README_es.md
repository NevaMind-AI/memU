![MemU Banner](../assets/banner.png)

<div align="center">

# memU

### Memoria Proactiva Siempre Activa para Agentes de IA

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](README_en.md) | [中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md)**

</div>

---

memU es un framework de memoria construido para **agentes proactivos 24/7**.
Está diseñado para uso prolongado y **reduce enormemente el costo de tokens LLM** de mantener agentes siempre en línea, haciendo que los agentes siempre activos y en evolución sean prácticos en sistemas de producción.
memU **captura y comprende continuamente la intención del usuario**. Incluso sin un comando, el agente puede detectar lo que estás a punto de hacer y actuar por sí mismo.

---

## 🤖 [OpenClaw (Moltbot, Clawdbot) Alternative](https://memu.bot)

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/memUbot.png" />

- **Download-and-use and simple** to get started.
- Builds long-term memory to **understand user intent** and act proactively.
- **Cuts LLM token cost** with smaller context.

Try now: [memU bot](https://memu.bot)

---

## 🗃️ Memoria como Sistema de Archivos, Sistema de Archivos como Memoria

memU trata la **memoria como un sistema de archivos**—estructurada, jerárquica e instantáneamente accesible.

| Sistema de Archivos | Memoria memU |
|--------------------|--------------|
| 📁 Carpetas | 🏷️ Categorías (temas auto-organizados) |
| 📄 Archivos | 🧠 Elementos de Memoria (hechos, preferencias, habilidades extraídas) |
| 🔗 Enlaces simbólicos | 🔄 Referencias cruzadas (memorias relacionadas enlazadas) |
| 📂 Puntos de montaje | 📥 Recursos (conversaciones, documentos, imágenes) |

**Por qué esto importa:**
- **Navega memorias** como si exploraras directorios—profundiza desde categorías amplias a hechos específicos
- **Monta nuevo conocimiento** instantáneamente—conversaciones y documentos se convierten en memoria consultable
- **Enlaza todo cruzadamente**—las memorias se referencian entre sí, construyendo un grafo de conocimiento conectado
- **Persistente y portable**—exporta, respalda y transfiere memoria como archivos

```
memory/
├── preference.md
├── soul.md
└── xxx.md

MEMORY.md

skill/
├── {skill_name}/
│   └── SKILL.md
└── {another_skill_name}/
    └── SKILL.md

SKILL.md

INDEX.md
```

Así como un sistema de archivos convierte bytes crudos en datos organizados, memU transforma interacciones crudas en **inteligencia estructurada, buscable y proactiva**.

---

## ⭐️ Dale una estrella al repositorio

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />
Si encuentras memU útil o interesante, te agradeceríamos mucho una estrella en GitHub ⭐️.

---


## ✨ Características Principales

| Capacidad | Descripción |
|-----------|-------------|
| 🤖 **Agente Proactivo 24/7** | Agente de memoria siempre activo que trabaja continuamente en segundo plano—nunca duerme, nunca olvida |
| 🎯 **Captura de Intención del Usuario** | Comprende y recuerda automáticamente objetivos, preferencias y contexto del usuario a través de sesiones |
| 💰 **Eficiente en Costos** | Reduce costos de tokens a largo plazo mediante caché de insights y evitando llamadas LLM redundantes |
---

## 🔄 Cómo Funciona la Memoria Proactiva

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

## 🎯 Casos de Uso Proactivos

### 1. **Recomendación de Información**
*El agente monitorea intereses y muestra proactivamente contenido relevante*
```python
# El usuario ha estado investigando temas de IA
MemU rastrea: historial de lectura, artículos guardados, consultas de búsqueda

# Cuando llega nuevo contenido:
Agente: "Encontré 3 nuevos papers sobre optimización RAG que se alinean con
        tu investigación reciente sobre sistemas de recuperación. Un autor
        (Dr. Chen) que has citado antes publicó ayer."

# Comportamientos proactivos:
- Aprende preferencias de temas de patrones de navegación
- Rastrea preferencias de credibilidad de autor/fuente
- Filtra ruido basado en historial de interacción
- Programa recomendaciones para atención óptima
```

### 2. **Gestión de Email**
*El agente aprende patrones de comunicación y maneja correspondencia rutinaria*
```python
# MemU observa patrones de email con el tiempo:
- Plantillas de respuesta para escenarios comunes
- Contactos prioritarios y palabras clave urgentes
- Preferencias de programación y disponibilidad
- Variaciones de estilo de escritura y tono

# Asistencia proactiva de email:
Agente: "Tienes 12 nuevos emails. He redactado respuestas para 3 solicitudes
        rutinarias y marcado 2 elementos urgentes de tus contactos prioritarios.
        ¿Debería también reprogramar la reunión de mañana basándome en el
        conflicto que mencionó John?"

# Acciones autónomas:
✓ Redactar respuestas conscientes del contexto
✓ Categorizar y priorizar bandeja de entrada
✓ Detectar conflictos de programación
✓ Resumir hilos largos con decisiones clave
```

### 3. **Trading y Monitoreo Financiero**
*El agente rastrea contexto del mercado y comportamiento de inversión del usuario*
```python
# MemU aprende preferencias de trading:
- Tolerancia al riesgo de decisiones históricas
- Sectores y clases de activos preferidos
- Patrones de respuesta a eventos del mercado
- Disparadores de rebalanceo de portafolio

# Alertas proactivas:
Agente: "NVDA cayó 5% en trading after-hours. Basándome en tu comportamiento
        pasado, típicamente compras caídas tech superiores al 3%. Tu asignación
        actual permite $2,000 de exposición adicional manteniendo tu objetivo
        70/30 acciones-bonos."

# Monitoreo continuo:
- Rastrear alertas de precio vinculadas a umbrales definidos por usuario
- Correlacionar eventos de noticias con impacto en portafolio
- Aprender de recomendaciones ejecutadas vs. ignoradas
- Anticipar oportunidades de cosecha de pérdidas fiscales
```


...

---

## 🗂️ Arquitectura de Memoria Jerárquica

El sistema de tres capas de MemU permite tanto **consultas reactivas** como **carga proactiva de contexto**:

<img width="100%" alt="structure" src="../assets/structure.png" />

| Capa | Uso Reactivo | Uso Proactivo |
|------|--------------|---------------|
| **Recurso** | Acceso directo a datos originales | Monitoreo en segundo plano de nuevos patrones |
| **Elemento** | Recuperación de hechos específicos | Extracción en tiempo real de interacciones en curso |
| **Categoría** | Vista general a nivel de resumen | Ensamblaje automático de contexto para anticipación |

**Beneficios Proactivos:**
- **Auto-categorización**: Nuevas memorias se auto-organizan en temas
- **Detección de Patrones**: El sistema identifica temas recurrentes
- **Predicción de Contexto**: Anticipa qué información se necesitará después

---

## 🚀 Inicio Rápido

### Opción 1: Versión en la Nube

Experimenta la memoria proactiva instantáneamente:

👉 **[memu.so](https://memu.so)** - Servicio hospedado con aprendizaje continuo 7×24

Para despliegue empresarial con flujos de trabajo proactivos personalizados, contacta **info@nevamind.ai**

#### API en la Nube (v3)

| URL Base | `https://api.memu.so` |
|----------|----------------------|
| Auth | `Authorization: Bearer YOUR_API_KEY` |

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v3/memory/memorize` | Registrar tarea de aprendizaje continuo |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | Verificar estado de procesamiento en tiempo real |
| `POST` | `/api/v3/memory/categories` | Listar categorías auto-generadas |
| `POST` | `/api/v3/memory/retrieve` | Consultar memoria (soporta carga proactiva de contexto) |

📚 **[Documentación Completa de API](https://memu.pro/docs#cloud-version)**

---

### Opción 2: Auto-Hospedado

#### Instalación
```bash
pip install -e .
```

#### Ejemplo Básico

> **Requisitos**: Python 3.13+ y una clave API de OpenAI

**Probar Aprendizaje Continuo** (en memoria):
```bash
export OPENAI_API_KEY=your_api_key
cd tests
python test_inmemory.py
```

**Probar con Almacenamiento Persistente** (PostgreSQL):
```bash
# Iniciar PostgreSQL con pgvector
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Ejecutar prueba de aprendizaje continuo
export OPENAI_API_KEY=your_api_key
cd tests
python test_postgres.py
```

Ambos ejemplos demuestran **flujos de trabajo de memoria proactiva**:
1. **Ingesta Continua**: Procesar múltiples archivos secuencialmente
2. **Auto-Extracción**: Creación inmediata de memoria
3. **Recuperación Proactiva**: Presentación de memoria consciente del contexto

Ver [`tests/test_inmemory.py`](../tests/test_inmemory.py) y [`tests/test_postgres.py`](../tests/test_postgres.py) para detalles de implementación.

---

### Proveedores Personalizados de LLM y Embeddings

MemU soporta proveedores personalizados de LLM y embeddings más allá de OpenAI. Configúralos via `llm_profiles`:
```python
from memu import MemUService

service = MemUService(
    llm_profiles={
        # Perfil predeterminado para operaciones LLM
        "default": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "your_api_key",
            "chat_model": "qwen3-max",
            "client_backend": "sdk"  # "sdk" o "http"
        },
        # Perfil separado para embeddings
        "embedding": {
            "base_url": "https://api.voyageai.com/v1",
            "api_key": "your_voyage_api_key",
            "embed_model": "voyage-3.5-lite"
        }
    },
    # ... otra configuración
)
```

---

### Integración con OpenRouter

MemU soporta [OpenRouter](https://openrouter.ai) como proveedor de modelos, dándote acceso a múltiples proveedores de LLM a través de una sola API.

#### Configuración
```python
from memu import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openrouter",
            "client_backend": "httpx",
            "base_url": "https://openrouter.ai",
            "api_key": "your_openrouter_api_key",
            "chat_model": "anthropic/claude-3.5-sonnet",  # Cualquier modelo de OpenRouter
            "embed_model": "openai/text-embedding-3-small",  # Modelo de embedding
        },
    },
    database_config={
        "metadata_store": {"provider": "inmemory"},
    },
)
```

#### Variables de Entorno

| Variable | Descripción |
|----------|-------------|
| `OPENROUTER_API_KEY` | Tu clave API de OpenRouter de [openrouter.ai/keys](https://openrouter.ai/keys) |

#### Características Soportadas

| Característica | Estado | Notas |
|----------------|--------|-------|
| Completaciones de Chat | Soportado | Funciona con cualquier modelo de chat de OpenRouter |
| Embeddings | Soportado | Usa modelos de embedding de OpenAI via OpenRouter |
| Visión | Soportado | Usa modelos con capacidad de visión (ej., `openai/gpt-4o`) |

#### Ejecutar Pruebas de OpenRouter
```bash
export OPENROUTER_API_KEY=your_api_key

# Prueba de flujo completo (memorize + retrieve)
python tests/test_openrouter.py

# Pruebas específicas de embedding
python tests/test_openrouter_embedding.py

# Pruebas específicas de visión
python tests/test_openrouter_vision.py
```

Ver [`examples/example_4_openrouter_memory.py`](../examples/example_4_openrouter_memory.py) para un ejemplo completo funcional.

---

## 📖 APIs Principales

### `memorize()` - Pipeline de Aprendizaje Continuo

Procesa entradas en tiempo real y actualiza la memoria inmediatamente:

<img width="100%" alt="memorize" src="../assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",  # Ruta de archivo o URL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"}             # Opcional: limitar a un usuario
)

# Retorna inmediatamente con la memoria extraída:
{
    "resource": {...},      # Metadatos del recurso almacenado
    "items": [...],         # Elementos de memoria extraídos (disponibles instantáneamente)
    "categories": [...]     # Estructura de categorías auto-actualizada
}
```

**Características Proactivas:**
- Procesamiento sin demora—memorias disponibles inmediatamente
- Categorización automática sin etiquetado manual
- Referencia cruzada con memorias existentes para detección de patrones

### `retrieve()` - Inteligencia de Doble Modo

MemU soporta tanto **carga proactiva de contexto** como **consultas reactivas**:

<img width="100%" alt="retrieve" src="../assets/retrieve.png" />

#### Recuperación basada en RAG (`method="rag"`)

**Ensamblaje proactivo de contexto** rápido usando embeddings:

- ✅ **Contexto instantáneo**: Presentación de memoria en sub-segundos
- ✅ **Monitoreo en segundo plano**: Puede ejecutarse continuamente sin costos de LLM
- ✅ **Puntuación de similitud**: Identifica automáticamente las memorias más relevantes

#### Recuperación basada en LLM (`method="llm"`)

**Razonamiento anticipatorio** profundo para contextos complejos:

- ✅ **Predicción de intención**: LLM infiere lo que el usuario necesita antes de preguntar
- ✅ **Evolución de consulta**: Refina automáticamente la búsqueda mientras el contexto se desarrolla
- ✅ **Terminación temprana**: Se detiene cuando se recopila suficiente contexto

#### Comparación

| Aspecto | RAG (Contexto Rápido) | LLM (Razonamiento Profundo) |
|---------|----------------------|----------------------------|
| **Velocidad** | ⚡ Milisegundos | 🐢 Segundos |
| **Costo** | 💰 Solo embedding | 💰💰 Inferencia LLM |
| **Uso proactivo** | Monitoreo continuo | Carga de contexto activada |
| **Mejor para** | Sugerencias en tiempo real | Anticipación compleja |

#### Uso
```python
# Recuperación proactiva con historial de contexto
result = await service.retrieve(
    queries=[
        {"role": "user", "content": {"text": "¿Cuáles son sus preferencias?"}},
        {"role": "user", "content": {"text": "Cuéntame sobre los hábitos de trabajo"}}
    ],
    where={"user_id": "123"},  # Opcional: filtro de alcance
    method="rag"  # o "llm" para razonamiento más profundo
)

# Retorna resultados conscientes del contexto:
{
    "categories": [...],     # Áreas temáticas relevantes (auto-priorizadas)
    "items": [...],          # Hechos de memoria específicos
    "resources": [...],      # Fuentes originales para trazabilidad
    "next_step_query": "..." # Contexto de seguimiento predicho
}
```

**Filtrado Proactivo**: Usa `where` para delimitar el monitoreo continuo:
- `where={"user_id": "123"}` - Contexto específico del usuario
- `where={"agent_id__in": ["1", "2"]}` - Coordinación multi-agente
- Omitir `where` para conciencia de contexto global

> 📚 **Para documentación completa de API**, ver [SERVICE_API.md](../docs/SERVICE_API.md) - incluye patrones de flujo de trabajo proactivo, configuración de pipeline y manejo de actualizaciones en tiempo real.

---

## 💡 Escenarios Proactivos

### Ejemplo 1: Asistente que Siempre Aprende

Aprende continuamente de cada interacción sin comandos explícitos de memoria:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_1_conversation_memory.py
```

**Comportamiento Proactivo:**
- Extrae automáticamente preferencias de menciones casuales
- Construye modelos de relación a partir de patrones de interacción
- Presenta contexto relevante en conversaciones futuras
- Adapta el estilo de comunicación basándose en preferencias aprendidas

**Mejor para:** Asistentes personales de IA, soporte al cliente que recuerda, chatbots sociales

---

### Ejemplo 2: Agente Auto-Mejorador

Aprende de logs de ejecución y sugiere proactivamente optimizaciones:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_2_skill_extraction.py
```

**Comportamiento Proactivo:**
- Monitorea acciones y resultados del agente continuamente
- Identifica patrones en éxitos y fracasos
- Auto-genera guías de habilidades a partir de experiencia
- Sugiere proactivamente estrategias para tareas futuras similares

**Mejor para:** Automatización DevOps, auto-mejora de agentes, captura de conocimiento

---

### Ejemplo 3: Constructor de Contexto Multimodal

Unifica memoria a través de diferentes tipos de entrada para contexto comprehensivo:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_3_multimodal_memory.py
```

**Comportamiento Proactivo:**
- Referencia cruzada de texto, imágenes y documentos automáticamente
- Construye comprensión unificada a través de modalidades
- Presenta contexto visual cuando se discuten temas relacionados
- Anticipa necesidades de información combinando múltiples fuentes

**Mejor para:** Sistemas de documentación, plataformas de aprendizaje, asistentes de investigación

---

## 📊 Rendimiento

MemU alcanza **92.09% de precisión promedio** en el benchmark Locomo en todas las tareas de razonamiento, demostrando operaciones confiables de memoria proactiva.

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

Ver datos experimentales detallados: [memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 Ecosistema

| Repositorio | Descripción | Características Proactivas |
|-------------|-------------|---------------------------|
| **[memU](https://github.com/NevaMind-AI/memU)** | Motor principal de memoria proactiva | Pipeline de aprendizaje 7×24, auto-categorización |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | Backend con sincronización continua | Actualizaciones de memoria en tiempo real, triggers de webhook |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | Dashboard visual de memoria | Monitoreo de evolución de memoria en vivo |

**Enlaces Rápidos:**
- 🚀 [Probar MemU Cloud](https://app.memu.so/quick-start)
- 📚 [Documentación de API](https://memu.pro/docs)
- 💬 [Comunidad Discord](https://discord.gg/memu)

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

</div>

---

## 🤝 Cómo Contribuir

¡Damos la bienvenida a contribuciones de la comunidad! Ya sea arreglando bugs, agregando características o mejorando documentación, tu ayuda es apreciada.

### Comenzando

Para empezar a contribuir a MemU, necesitarás configurar tu entorno de desarrollo:

#### Prerrequisitos
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (gestor de paquetes Python)
- Git

#### Configurar Entorno de Desarrollo
```bash
# 1. Fork y clonar el repositorio
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# 2. Instalar dependencias de desarrollo
make install
```

El comando `make install` hará:
- Crear un entorno virtual usando `uv`
- Instalar todas las dependencias del proyecto
- Configurar hooks de pre-commit para verificaciones de calidad de código

#### Ejecutar Verificaciones de Calidad

Antes de enviar tu contribución, asegúrate de que tu código pase todas las verificaciones de calidad:
```bash
make check
```

El comando `make check` ejecuta:
- **Verificación de archivo lock**: Asegura consistencia de `pyproject.toml`
- **Hooks de pre-commit**: Lint de código con Ruff, formateo con Black
- **Verificación de tipos**: Ejecuta `mypy` para análisis de tipos estáticos
- **Análisis de dependencias**: Usa `deptry` para encontrar dependencias obsoletas

### Guías de Contribución

Para guías detalladas de contribución, estándares de código y prácticas de desarrollo, ver [CONTRIBUTING.md](../CONTRIBUTING.md).

**Tips rápidos:**
- Crear una nueva rama para cada característica o corrección de bug
- Escribir mensajes de commit claros
- Agregar tests para nueva funcionalidad
- Actualizar documentación según sea necesario
- Ejecutar `make check` antes de hacer push

---

## 📄 Licencia

[Apache License 2.0](../LICENSE.txt)

---

## 🌍 Comunidad

- **GitHub Issues**: [Reportar bugs y solicitar características](https://github.com/NevaMind-AI/memU/issues)
- **Discord**: [Unirse a la comunidad](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**: [Seguir @memU_ai](https://x.com/memU_ai)
- **Contacto**: info@nevamind.ai

---

<div align="center">

⭐ **¡Danos una estrella en GitHub** para recibir notificaciones de nuevos lanzamientos!

</div>
