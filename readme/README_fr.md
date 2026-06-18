![MemU Banner](../assets/banner.png)

<div align="center">

# memU

### Le système de fichiers comme mémoire, la mémoire façonne l'agent

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.com/invite/hQZntfGsbJ)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](README_en.md) | [中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md)**

</div>

---

memU est un **système de fichiers de mémoire** pour les agents d'IA.

Plutôt que d'aplatir tout ce qu'un agent apprend dans un unique prompt géant ou un blob vectoriel opaque, memU organise la mémoire comme vous organisez un ordinateur : sous la forme d'une arborescence navigable de fichiers Markdown lisibles par l'humain.

- **`MEMORY.md`** : la mémoire vivante de l'agent : qui est l'utilisateur, ses préférences, ses objectifs et les événements extraits de chaque source
- **`SKILL.md`** : les compétences et schémas d'outils appris : ce qui a fonctionné, ce qu'il faut éviter et comment reproduire les tâches récurrentes
- **`INDEX.md`** : la table des matières : une carte navigable de tous les fichiers de mémoire, pour que l'agent sache où chercher avant de lire
- **L'agent lit et écrit ces fichiers** : il utilise `memorize()` pour y écrire de nouvelles sources et `retrieve()` pour ne lire, à la demande, que les sections qui comptent

```txt
memory/
├── INDEX.md              ← carte de tout : catégories, fichiers et résumés
├── MEMORY.md             ← profil, préférences, objectifs et événements clés
└── skill/
    ├── {skill_name}/
    │   └── SKILL.md       ← une compétence ou un schéma d'outil appris
    └── {another_skill}/
        └── SKILL.md
```

**Le système de fichiers comme mémoire** : une surface hiérarchique et navigable où chaque mémoire remonte jusqu'à sa source.
**La mémoire façonne l'agent** : comme cette surface est structurée et auto-organisée, elle cesse d'être un stockage passif et devient la couche qui façonne la manière dont l'agent pense et agit.

---

## 🔄 Comment ça marche

Voyez cela comme deux opérations de système de fichiers : **écrire** des sources brutes dans une mémoire organisée, et **relire** les bons fichiers vers l'agent.

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

**Écrire dans le système de fichiers (`memorize`)**

1. **Ingérer (Ingest)** : stocke chaque source sous forme de `Resource` (le fichier brut) avec sa modalité et son emplacement d'origine
2. **Prétraiter (Preprocess)** : analyse le texte, légende les images/vidéos, transcrit l'audio et normalise les entrées
3. **Extraire (Extract)** : transforme le contenu brut en `MemoryItem`s typés (les fichiers) : mémoires de type profile, event, knowledge, behavior, skill ou tool
4. **Organiser (Organize)** : range les éléments dans des dossiers `MemoryCategory`, les relie entre eux, les vectorise et les résume en une arborescence navigable
5. **Persister (Persist)** : écrit les enregistrements, relations, embeddings et résumés de dossier via le backend configuré

**Lire depuis le système de fichiers (`retrieve`)**

6. **Récupérer (Retrieve)** : parcourt les dossiers et ne renvoie que les fichiers pertinents pour l'utilisateur, l'agent, la session ou la tâche en cours

---

## 🗂️ Le système de fichiers de mémoire

La sortie principale de memU est une arborescence de mémoire navigable — dossiers, fichiers et les artefacts source qui se trouvent derrière — persistée via des contrats de dépôt et renvoyée sous forme de dictionnaires par `memorize()` et `retrieve()`.

```txt
MemoryCategory                       ← dossier : un thème avec un résumé en évolution
├── name, description, summary
├── embedding
└── MemoryItem[]                     ← fichiers : des mémoires atomiques et typées
    ├── memory_type: profile | event | knowledge | behavior | skill | tool
    ├── summary, extra, happened_at, embedding
    └── Resource                     ← source : le fichier brut dont provient cette mémoire
        └── url, modality, local_path, caption, embedding
```

| Enregistrement | Rôle dans le système de fichiers | Utilisé pour |
|--------|------------------|---------|
| `MemoryCategory` | **Dossier** : regroupe les mémoires liées et tient un résumé au niveau du thème | Charger un contexte compact pour les requêtes larges |
| `MemoryItem` | **Fichier** : mémoire atomique typée avec un résumé et des métadonnées optionnelles | Injecter des faits, préférences, événements, compétences et schémas d'outils précis |
| `Resource` | **Artefact source** : le fichier d'origine derrière une mémoire, avec légende/texte | Remonter le contexte jusqu'à son origine |
| `CategoryItem` | **Lien** : l'arête qui classe un élément sous un dossier | Naviguer entre les mémoires liées sans retraiter la source |

Cela donne aux agents un système de fichiers de mémoire stable : ils ingèrent les sources brutes une seule fois, puis demandent des fichiers délimités et classés plutôt que de relire chaque artefact source.

---

## 🧩 Ce que memU construit

Chaque couche du système de fichiers est stockée sous forme d'enregistrement structuré :

| Couche | Ce qu'elle représente | Pourquoi les agents l'utilisent |
|-------|--------------------|-------------------|
| **MemoryCategory** | Dossier auto-généré : un thème avec un résumé en évolution | Charger un contexte de haut niveau avant de plonger dans les détails |
| **MemoryItem** | Un fichier : mémoire structurée atomique avec un type et un résumé | Injecter des faits, préférences, événements, compétences et schémas d'outils précis |
| **Resource** | Artefact source derrière un fichier : conversation, document, image, vidéo, audio, URL ou fichier | Remonter la mémoire jusqu'à son origine |
| **CategoryItem** | Le lien qui classe un élément sous un dossier | Naviguer entre les mémoires liées sans retraiter la source |
| **Embedding** | Index vectoriel couvrant dossiers, fichiers et sources | Récupérer le contexte pertinent avec une faible latence |

Exemple de sortie de `memorize()` :

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

Un agent peut ensuite appeler `retrieve()` pour obtenir une charge de contexte délimitée et classée par pertinence :

```python
context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What context matters for this launch task?"}}],
    where={"user_id": "123"},
)
```

---

## ⭐️ Mettez une étoile au dépôt

<img width="100%" src="https://github.com/NevaMind-AI/memU/blob/main/assets/star.gif" />

Si vous trouvez memU utile ou intéressant, une étoile ⭐️ sur GitHub serait grandement appréciée.

---

## ✨ Fonctionnalités principales

| Capacité | Description |
|------------|-------------|
| 🗂️ **Ingestion multimodale** | Écrit conversations, documents, images, vidéos, audio, URL, journaux et fichiers locaux dans la mémoire |
| 📁 **Système de fichiers de mémoire** | Persiste dossiers (catégories), fichiers (éléments), artefacts source, liens, résumés et embeddings |
| 🧠 **Extraction de mémoire typée** | Extrait des mémoires profile, event, knowledge, behavior, skill et tool à partir de sources brutes |
| 🧭 **Dossiers auto-organisés** | Construit automatiquement catégories, liens, résumés et embeddings sans étiquetage manuel |
| 🤖 **Récupération prête pour les agents** | Lit un contexte délimité et classé pouvant être injecté dans n'importe quel workflow d'agent |
| 🧱 **Stockage enfichable** | Utilise des backends in-memory, SQLite ou Postgres avec les mêmes contrats de dépôt |
| 🔀 **Routage de LLM basé sur les profils** | Achemine les tâches de chat, embeddings, vision et transcription via des profils de LLM configurables |

---

## 🎯 Cas d'usage

### 1. **Mémoire de conversation**
*Transforme les journaux de chat en préférences, objectifs, événements et contexte relationnel de l'utilisateur.*

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

### 2. **Contexte d'espace de travail pour les agents de codage**
*Convertit documents, notes de PR, journaux et décisions de conception en mémoire de projet réutilisable.*

```python
await service.memorize(resource_url="docs/architecture.md", modality="document")
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "How should I structure this module?"}}],
)
```

### 3. **Couche de connaissances multimodale**
*Extrait des faits interrogeables à partir de documents, captures d'écran, images, vidéos et notes audio.*

```python
await service.memorize(resource_url="examples/resources/docs/doc1.txt", modality="document")
await service.memorize(resource_url="examples/resources/images/image1.png", modality="image")
# Audio is supported for your own .mp3/.wav/.m4a files.
await service.memorize(resource_url="meeting-audio.mp3", modality="audio")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What matters for the next research plan?"}}],
)
```

### 4. **Apprentissage des outils et des agents**
*Transforme les traces d'exécution en mémoires d'outils qui indiquent aux agents futurs quand utiliser un outil et quelles erreurs éviter.*

```python
await service.memorize(resource_url="examples/resources/logs/log1.txt", modality="document")

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "Which tools worked for config editing?"}}],
)
```

---

## 🗂️ Architecture

Le système de fichiers de mémoire est assez hiérarchique pour être parcouru et assez structuré pour une récupération directe :

<img width="100%" alt="structure" src="../assets/structure.png" />

| Couche | Rôle principal | Rôle dans la récupération |
|-------|--------------|----------------|
| **Category (dossier)** | Maintenir des résumés au niveau du thème | Assembler un contexte compact pour les requêtes larges |
| **Item (fichier)** | Stocker des mémoires atomiques typées | Charger des faits, événements, préférences, compétences et schémas d'outils précis |
| **Resource (source)** | Préserver les artefacts source et les légendes | Rappeler le contexte d'origine lorsque les résumés d'élément/catégorie ne suffisent pas |

Consultez [docs/architecture.md](../docs/architecture.md) pour la vue à l'exécution de `MemoryService`, des pipelines de workflow, des backends de stockage et du routage de LLM.

---

## 🚀 Démarrage rapide

### Option 1 : Version cloud

👉 **[memu.so](https://memu.so)** : API hébergée pour l'ingestion gérée, la mémoire structurée et la récupération

Pour un déploiement en entreprise : **info@nevamind.ai**

#### Cloud API (v3)

| Base URL | `https://api.memu.so` |
|----------|----------------------|
| Auth | `Authorization: Bearer <token>` |

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v3/memory/memorize` | Ingère des données brutes et construit une mémoire structurée |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | Vérifie l'état du traitement |
| `POST` | `/api/v3/memory/categories` | Liste les catégories auto-générées |
| `POST` | `/api/v3/memory/retrieve` | Interroge la mémoire pour obtenir le contexte de l'agent |

📚 **[Documentation complète de l'API](https://memu.pro/docs#cloud-version)**

---

### Option 2 : Auto-hébergé

#### Installation

À partir d'un clone de ce dépôt :

```bash
uv sync
# ou, pour la configuration de développement complète :
make install
```

Pour installer le paquet publié à la place :

```bash
pip install memu-py
```

> **Prérequis** : Python 3.13+. Les exemples par défaut utilisent OpenAI ; définissez donc `OPENAI_API_KEY` ou passez un autre fournisseur via `llm_profiles`.

**Exécuter un script de test en mémoire :**
```bash
export OPENAI_API_KEY=your_key
cd tests
uv run python test_inmemory.py
```

**Exécuter avec PostgreSQL + pgvector :**
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

### Fournisseurs de LLM et d'embeddings personnalisés

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

### Intégration OpenRouter

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

### `memorize()` : structurer les données brutes

<img width="100%" alt="memorize" src="../assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",    # chemin de fichier local ou URL HTTP
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"},            # optionnel : délimiter à un utilisateur ou un agent
)
# Renvoie une fois le traitement terminé :
# { "resource": {...}, "items": [...], "categories": [...], "relations": [...] }
```

- Convertit l'entrée brute en éléments de mémoire typés
- Catégorise et vectorise les éléments sans étiquetage manuel
- Préserve les ressources source et les relations élément-catégorie

---

### `retrieve()` : charger le contexte de l'agent

<img width="100%" alt="retrieve" src="../assets/retrieve.png" />

```python
# La stratégie de récupération est définie une fois sur le service via retrieve_config :
#   MemoryService(retrieve_config={"method": "rag"})   # rappel vecteurs d'abord
#   MemoryService(retrieve_config={"method": "llm"})   # rappel classé par LLM
result = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "What are their preferences?"}}],
    where={"user_id": "123"},   # filtre de portée
)
# Renvoie :
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

| `retrieve_config.method` | Comportement | Coût | Idéal pour |
|--------------------------|----------|------|----------|
| `rag` | Rappel des catégories/éléments/ressources avec vecteurs d'abord, avec routage LLM et vérifications de suffisance optionnels activés par défaut | Embeddings plus appels LLM, sauf si `route_intention` et `sufficiency_check` sont désactivés | Rappel délimité et rapide avec un raisonnement contrôlable |
| `llm` | Rappel des catégories/éléments/ressources classé par LLM | Classement par LLM à chaque niveau | Classement sémantique plus profond |

---

## 💡 Exemples de workflows

### Assistant en apprentissage permanent
```bash
export OPENAI_API_KEY=your_key
uv run python examples/example_1_conversation_memory.py
```
Extrait automatiquement les préférences, construit des modèles de relation et fait remonter le contexte pertinent dans les conversations futures.

### Agent qui s'améliore lui-même
```bash
uv run python examples/example_2_skill_extraction.py
```
Surveille les actions de l'agent, identifie les schémas de réussites et d'échecs, et génère automatiquement des guides de compétences à partir de l'expérience.

### Constructeur de contexte multimodal
```bash
uv run python examples/example_3_multimodal_memory.py
```
Recoupe automatiquement texte, images et documents dans une couche de mémoire unifiée.

---

## 📊 Performances

memU atteint une **précision moyenne de 92,09 %** sur le benchmark Locomo, sur l'ensemble des tâches de raisonnement.

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

Voir les résultats détaillés : [memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 Écosystème

| Dépôt | Description |
|------------|-------------|
| **[memU](https://github.com/NevaMind-AI/memU)** | Système de fichiers de mémoire central : ingestion, extraction, récupération |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | Backend avec synchronisation en temps réel et déclencheurs webhook |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | Tableau de bord visuel pour explorer et surveiller la mémoire |

**Liens rapides :**
- 🚀 [Essayer MemU Cloud](https://app.memu.so/quick-start)
- 📚 [Documentation de l'API](https://memu.pro/docs)
- 💬 [Communauté Discord](https://discord.com/invite/hQZntfGsbJ)

---

## 🤝 Partenaires

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

## 🤝 Contribuer

```bash
# Forkez et clonez
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# Installez les dépendances de développement
make install

# Lancez les contrôles qualité avant de soumettre
make check
```

Consultez [CONTRIBUTING.md](../CONTRIBUTING.md) pour les directives complètes.

**Prérequis :** Python 3.13+, [uv](https://github.com/astral-sh/uv), Git

---

## 📄 Licence

[Apache License 2.0](../LICENSE.txt)

---

## 🌍 Communauté

- **GitHub Issues** : [Signaler des bugs et demander des fonctionnalités](https://github.com/NevaMind-AI/memU/issues)
- **Discord** : [Rejoindre la communauté](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)** : [Suivre @memU_ai](https://x.com/memU_ai)
- **Contact** : info@nevamind.ai

---

<div align="center">

⭐ **Mettez-nous une étoile sur GitHub** pour être averti des nouvelles versions !

</div>
