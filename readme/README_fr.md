![MemU Banner](../assets/banner.png)

<div align="center">

# memU

### Mémoire Proactive Toujours Active pour les Agents IA

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)

<a href="https://trendshift.io/repositories/17374" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17374" alt="NevaMind-AI%2FmemU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**[English](README_en.md) | [中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Español](README_es.md) | [Français](README_fr.md)**

</div>

---

memU est un framework de mémoire conçu pour les **agents proactifs 24/7**.
Il est conçu pour une utilisation prolongée et **réduit considérablement le coût en tokens LLM** pour maintenir les agents toujours en ligne, rendant les agents toujours actifs et évolutifs pratiques dans les systèmes de production.
memU **capture et comprend continuellement l'intention de l'utilisateur**. Même sans commande, l'agent peut détecter ce que vous êtes sur le point de faire et agir de lui-même.

---

## 🤖 [OpenClaw (Moltbot, Clawdbot) Alternative](https://memu.bot)

<img width="100%" src="https://github.com/NevaMind-AI/MemU/blob/main/assets/memUbot.png" />

- **Download-and-use and simple** to get started.
- Builds long-term memory to **understand user intent** and act proactively.
- **Cuts LLM token cost** with smaller context.

Try now: [memU bot](https://memu.bot)

---

## 🗃️ La Mémoire comme Système de Fichiers, le Système de Fichiers comme Mémoire

memU traite la **mémoire comme un système de fichiers**—structurée, hiérarchique et instantanément accessible.

| Système de Fichiers | Mémoire memU |
|--------------------|--------------|
| 📁 Dossiers | 🏷️ Catégories (sujets auto-organisés) |
| 📄 Fichiers | 🧠 Éléments de Mémoire (faits, préférences, compétences extraites) |
| 🔗 Liens symboliques | 🔄 Références croisées (mémoires liées connectées) |
| 📂 Points de montage | 📥 Ressources (conversations, documents, images) |

**Pourquoi c'est important :**
- **Naviguez dans les mémoires** comme dans des répertoires—explorez des catégories larges jusqu'aux faits spécifiques
- **Montez de nouvelles connaissances** instantanément—les conversations et documents deviennent de la mémoire interrogeable
- **Liez tout de manière croisée**—les mémoires se référencent mutuellement, construisant un graphe de connaissances connecté
- **Persistant et portable**—exportez, sauvegardez et transférez la mémoire comme des fichiers

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

Tout comme un système de fichiers transforme des octets bruts en données organisées, memU transforme les interactions brutes en **intelligence structurée, recherchable et proactive**.

---

## ⭐️ Mettez une étoile au dépôt

<img width="100%" src="https://github.com/NevaMind-AI/MemU/blob/main/assets/star.gif" />
Si vous trouvez memU utile ou intéressant, une étoile GitHub ⭐️ serait grandement appréciée.

---


## ✨ Fonctionnalités Principales

| Capacité | Description |
|----------|-------------|
| 🤖 **Agent Proactif 24/7** | Agent de mémoire toujours actif qui travaille continuellement en arrière-plan—ne dort jamais, n'oublie jamais |
| 🎯 **Capture d'Intention Utilisateur** | Comprend et mémorise automatiquement les objectifs, préférences et contexte de l'utilisateur à travers les sessions |
| 💰 **Économique** | Réduit les coûts de tokens à long terme en cachant les insights et en évitant les appels LLM redondants |
---

## 🔄 Comment Fonctionne la Mémoire Proactive

```bash
pip install "memu-py[claude]"
# From a source checkout, use: uv sync --extra claude
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
# Optional when using memory.platform instead of memory.local:
export MEMU_API_KEY="..."
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

## 🎯 Cas d'Usage Proactifs

### 1. **Recommandation d'Information**
*L'agent surveille les intérêts et affiche proactivement du contenu pertinent*
```python
# L'utilisateur recherche des sujets sur l'IA
MemU suit: historique de lecture, articles sauvegardés, requêtes de recherche

# Quand du nouveau contenu arrive:
Agent: "J'ai trouvé 3 nouveaux articles sur l'optimisation RAG qui
        correspondent à vos recherches récentes sur les systèmes de
        récupération. Un auteur (Dr. Chen) que vous avez cité a publié hier."

# Comportements proactifs:
- Apprend les préférences de sujets des patterns de navigation
- Suit les préférences de crédibilité auteur/source
- Filtre le bruit selon l'historique d'engagement
- Planifie les recommandations pour attention optimale
```

### 2. **Gestion d'Email**
*L'agent apprend les patterns de communication et gère la correspondance routinière*
```python
# MemU observe les patterns email au fil du temps:
- Templates de réponse pour scénarios courants
- Contacts prioritaires et mots-clés urgents
- Préférences de planning et disponibilité
- Variations de style d'écriture et de ton

# Assistance email proactive:
Agent: "Vous avez 12 nouveaux emails. J'ai rédigé des réponses pour 3
        demandes routinières et marqué 2 éléments urgents de vos contacts
        prioritaires. Dois-je aussi reprogrammer la réunion de demain
        selon le conflit mentionné par John?"

# Actions autonomes:
✓ Rédiger des réponses contextuelles
✓ Catégoriser et prioriser la boîte de réception
✓ Détecter les conflits de planning
✓ Résumer les longs fils avec décisions clés
```

### 3. **Trading & Surveillance Financière**
*L'agent suit le contexte marché et le comportement d'investissement utilisateur*
```python
# MemU apprend les préférences de trading:
- Tolérance au risque des décisions historiques
- Secteurs et classes d'actifs préférés
- Patterns de réponse aux événements marché
- Déclencheurs de rééquilibrage de portefeuille

# Alertes proactives:
Agent: "NVDA a chuté de 5% en after-hours. Selon votre comportement passé,
        vous achetez typiquement les baisses tech supérieures à 3%. Votre
        allocation actuelle permet $2,000 d'exposition supplémentaire tout
        en maintenant votre cible 70/30 actions-obligations."

# Surveillance continue:
- Suivre les alertes prix liées aux seuils définis
- Corréler événements d'actualité et impact portefeuille
- Apprendre des recommandations exécutées vs. ignorées
- Anticiper les opportunités de récolte de pertes fiscales
```


...

---

## 🗂️ Architecture de Mémoire Hiérarchique

Le système à trois couches de MemU permet à la fois **les requêtes réactives** et **le chargement proactif de contexte** :

<img width="100%" alt="structure" src="../assets/structure.png" />

| Couche | Usage Réactif | Usage Proactif |
|--------|---------------|----------------|
| **Ressource** | Accès direct aux données originales | Surveillance en arrière-plan des nouveaux patterns |
| **Élément** | Récupération de faits ciblée | Extraction en temps réel des interactions en cours |
| **Catégorie** | Vue d'ensemble au niveau résumé | Assemblage automatique de contexte pour anticipation |

**Avantages Proactifs:**
- **Auto-catégorisation**: Les nouvelles mémoires s'auto-organisent en sujets
- **Détection de Patterns**: Le système identifie les thèmes récurrents
- **Prédiction de Contexte**: Anticipe quelle information sera nécessaire ensuite

---

## 🚀 Démarrage Rapide

### Option 1: Version Cloud

Expérimentez la mémoire proactive instantanément:

👉 **[memu.so](https://memu.so)** - Service hébergé avec apprentissage continu 7×24

Pour un déploiement entreprise avec des workflows proactifs personnalisés, contactez **info@nevamind.ai**

#### API Cloud (v3)

| URL de Base | `https://api.memu.so` |
|-------------|----------------------|
| Auth | `Authorization: Bearer YOUR_API_KEY` |

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/v3/memory/memorize` | Enregistrer une tâche d'apprentissage continu |
| `GET` | `/api/v3/memory/memorize/status/{task_id}` | Vérifier le statut de traitement en temps réel |
| `POST` | `/api/v3/memory/categories` | Lister les catégories auto-générées |
| `POST` | `/api/v3/memory/retrieve` | Interroger la mémoire (supporte le chargement proactif de contexte) |

📚 **[Documentation Complète de l'API](https://memu.pro/docs#cloud-version)**

---

### Option 2: Auto-Hébergé

#### Installation
```bash
pip install memu-py
```

#### Exemple de Base

> **Prérequis**: Python 3.12+ et une clé API OpenAI

**Tester l'Apprentissage Continu** (en mémoire):
```bash
export OPENAI_API_KEY=your_api_key
python examples/getting_started_robust.py
```

**Tester avec Stockage Persistant** (PostgreSQL):
```bash
# Démarrer PostgreSQL avec pgvector
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Exécuter le test d'apprentissage continu
uv sync --extra postgres
export OPENAI_API_KEY=your_api_key
export MEMU_RUN_POSTGRES_TESTS=1
uv run python -m pytest tests/test_postgres.py
```

Les deux exemples démontrent **les workflows de mémoire proactive**:
1. **Ingestion Continue**: Traiter plusieurs fichiers séquentiellement
2. **Auto-Extraction**: Création immédiate de mémoire
3. **Récupération Proactive**: Affichage de mémoire contextuel

Voir [`tests/test_inmemory.py`](../tests/test_inmemory.py), [`tests/test_sqlite.py`](../tests/test_sqlite.py)
et [`tests/test_postgres.py`](../tests/test_postgres.py) pour les détails d'implémentation. Les vérifications live LLM
in-memory et SQLite sont opt-in avec `MEMU_RUN_LIVE_LLM_TESTS=1`.

---

### Fournisseurs LLM et Embeddings Personnalisés

MemU supporte des fournisseurs LLM et embeddings personnalisés au-delà d'OpenAI. Configurez-les via `llm_profiles`:
```python
from memu import MemUService

service = MemUService(
    llm_profiles={
        # Profil par défaut pour les opérations LLM
        "default": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "MEMU_QWEN_API_KEY",
            "chat_model": "qwen3-max",
            "client_backend": "sdk"  # "sdk", "httpx" ou "lazyllm_backend"
        },
        # Profil séparé pour les embeddings
        "embedding": {
            "base_url": "https://api.voyageai.com/v1",
            "api_key": "VOYAGE_API_KEY",
            "embed_model": "voyage-3.5-lite"
        }
    },
    # ... autre configuration
)
```

The `lazyllm_backend` adapter is optional. Install it with
`pip install "memu-py[lazyllm]"` or, from a source checkout,
`uv sync --extra lazyllm`.

Optional LazyLLM live check:

```bash
uv sync --extra lazyllm
export MEMU_QWEN_API_KEY=your_api_key
export MEMU_RUN_LAZYLLM_TESTS=1
uv run python -m pytest tests/test_lazyllm.py
```

---

### Intégration OpenRouter

MemU supporte [OpenRouter](https://openrouter.ai) comme fournisseur de modèles, vous donnant accès à plusieurs fournisseurs LLM via une seule API.

#### Configuration
```python
from memu import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openrouter",
            "client_backend": "httpx",
            "base_url": "https://openrouter.ai",
            "api_key": "OPENROUTER_API_KEY",
            "chat_model": "anthropic/claude-3.5-sonnet",  # N'importe quel modèle OpenRouter
            "embed_model": "openai/text-embedding-3-small",  # Modèle d'embedding
        },
    },
    database_config={
        "metadata_store": {"provider": "inmemory"},
    },
)
```

#### Variables d'Environnement

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | Votre clé API OpenRouter de [openrouter.ai/keys](https://openrouter.ai/keys) |

#### Fonctionnalités Supportées

| Fonctionnalité | Statut | Notes |
|----------------|--------|-------|
| Complétion de Chat | Supporté | Fonctionne avec n'importe quel modèle de chat OpenRouter |
| Embeddings | Supporté | Utilisez les modèles d'embedding OpenAI via OpenRouter |
| Vision | Supporté | Utilisez des modèles avec capacité vision (ex., `openai/gpt-4o`) |

#### Exécuter les Tests OpenRouter
```bash
export OPENROUTER_API_KEY=your_api_key
export MEMU_RUN_OPENROUTER_TESTS=1

# Test de workflow complet (memorize + retrieve)
uv run python -m pytest tests/test_openrouter.py
```

Voir [`examples/example_4_openrouter_memory.py`](../examples/example_4_openrouter_memory.py) pour un exemple complet fonctionnel.

---

## 📖 APIs Principales

### `memorize()` - Pipeline d'Apprentissage Continu

Traite les entrées en temps réel et met à jour la mémoire immédiatement:

<img width="100%" alt="memorize" src="../assets/memorize.png" />

```python
result = await service.memorize(
    resource_url="path/to/file.json",  # Chemin de fichier ou URL
    modality="conversation",            # conversation | document | image | video | audio
    user={"user_id": "123"}             # Optionnel: limiter à un utilisateur
)

# Retourne immédiatement avec la mémoire extraite:
{
    "resource": {...},      # Métadonnées de ressource stockées
    "items": [...],         # Éléments de mémoire extraits (disponibles instantanément)
    "categories": [...]     # Structure de catégories auto-mise à jour
}
```

**Fonctionnalités Proactives:**
- Traitement sans délai—mémoires disponibles immédiatement
- Catégorisation automatique sans étiquetage manuel
- Référence croisée avec les mémoires existantes pour détection de patterns

### `retrieve()` - Intelligence Double Mode

MemU supporte à la fois **le chargement proactif de contexte** et **les requêtes réactives**:

<img width="100%" alt="retrieve" src="../assets/retrieve.png" />

#### Récupération basée sur RAG (`method="rag"`)

**Assemblage proactif de contexte** rapide utilisant les embeddings:

- ✅ **Contexte instantané**: Affichage de mémoire en sous-seconde
- ✅ **Surveillance en arrière-plan**: Peut s'exécuter continuellement sans coûts LLM
- ✅ **Score de similarité**: Identifie automatiquement les mémoires les plus pertinentes

#### Récupération basée sur LLM (`method="llm"`)

**Raisonnement anticipatoire** profond pour contextes complexes:

- ✅ **Prédiction d'intention**: LLM infère ce dont l'utilisateur a besoin avant de demander
- ✅ **Évolution de requête**: Affine automatiquement la recherche au fur et à mesure que le contexte se développe
- ✅ **Terminaison précoce**: S'arrête quand suffisamment de contexte est collecté

#### Comparaison

| Aspect | RAG (Contexte Rapide) | LLM (Raisonnement Profond) |
|--------|----------------------|---------------------------|
| **Vitesse** | ⚡ Millisecondes | 🐢 Secondes |
| **Coût** | 💰 Embedding seulement | 💰💰 Inférence LLM |
| **Usage proactif** | Surveillance continue | Chargement de contexte déclenché |
| **Meilleur pour** | Suggestions temps réel | Anticipation complexe |

#### Utilisation
```python
# Récupération proactive avec historique de contexte
result = await service.retrieve(
    queries=[
        {"role": "user", "content": "Quelles sont leurs préférences?"},
        {"role": "user", "content": "Parle-moi des habitudes de travail"}
    ],
    where={"user_id": "123"},  # Optionnel: filtre de portée
    method="rag"  # ou "llm" pour raisonnement plus profond
)

# Retourne des résultats contextuels:
{
    "categories": [...],     # Domaines thématiques pertinents (auto-priorisés)
    "items": [...],          # Faits de mémoire spécifiques
    "resources": [...],      # Sources originales pour traçabilité
    "next_step_query": "..." # Contexte de suivi prédit
}
```

**Filtrage Proactif**: Utilisez `where` pour délimiter la surveillance continue:
- `where={"user_id": "123"}` - Contexte spécifique à l'utilisateur
- `where={"agent_id__in": ["1", "2"]}` - Coordination multi-agent
- Omettre `where` pour conscience de contexte globale

> 📚 **Pour la documentation API complète**, voir [memu.pro/docs](https://memu.pro/docs) - inclut les patterns de workflow proactif, configuration de pipeline et gestion des mises à jour en temps réel.

---

## 💡 Scénarios Proactifs

### Exemple 1: Assistant Toujours Apprenant

Apprend continuellement de chaque interaction sans commandes de mémoire explicites:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_1_conversation_memory.py
```

**Comportement Proactif:**
- Extrait automatiquement les préférences des mentions occasionnelles
- Construit des modèles de relation à partir des patterns d'interaction
- Affiche le contexte pertinent dans les conversations futures
- Adapte le style de communication basé sur les préférences apprises

**Meilleur pour:** Assistants IA personnels, support client qui se souvient, chatbots sociaux

---

### Exemple 2: Agent Auto-Améliorant

Apprend des logs d'exécution et suggère proactivement des optimisations:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_2_skill_extraction.py
```

**Comportement Proactif:**
- Surveille les actions et résultats de l'agent continuellement
- Identifie les patterns dans les succès et échecs
- Auto-génère des guides de compétences à partir de l'expérience
- Suggère proactivement des stratégies pour des tâches futures similaires

**Meilleur pour:** Automatisation DevOps, auto-amélioration d'agent, capture de connaissances

---

### Exemple 3: Constructeur de Contexte Multimodal

Unifie la mémoire à travers différents types d'entrée pour un contexte complet:
```bash
export OPENAI_API_KEY=your_api_key
python examples/example_3_multimodal_memory.py
```

**Comportement Proactif:**
- Référence croisée de texte, images et documents automatiquement
- Construit une compréhension unifiée à travers les modalités
- Affiche le contexte visuel lors de la discussion de sujets associés
- Anticipe les besoins d'information en combinant plusieurs sources

**Meilleur pour:** Systèmes de documentation, plateformes d'apprentissage, assistants de recherche

---

## 📊 Performance

MemU atteint **92.09% de précision moyenne** sur le benchmark Locomo à travers toutes les tâches de raisonnement, démontrant des opérations de mémoire proactive fiables.

<img width="100%" alt="benchmark" src="https://github.com/user-attachments/assets/6fec4884-94e5-4058-ad5c-baac3d7e76d9" />

Voir les données expérimentales détaillées: [memU-experiment](https://github.com/NevaMind-AI/memU-experiment)

---

## 🧩 Écosystème

| Dépôt | Description | Fonctionnalités Proactives |
|-------|-------------|---------------------------|
| **[memU](https://github.com/NevaMind-AI/MemU)** | Moteur principal de mémoire proactive | Pipeline d'apprentissage 7×24, auto-catégorisation |
| **[memU-server](https://github.com/NevaMind-AI/memU-server)** | Backend avec synchronisation continue | Mises à jour de mémoire en temps réel, déclencheurs webhook |
| **[memU-ui](https://github.com/NevaMind-AI/memU-ui)** | Dashboard visuel de mémoire | Surveillance de l'évolution de la mémoire en direct |

**Liens Rapides:**
- 🚀 [Essayer MemU Cloud](https://app.memu.so/quick-start)
- 📚 [Documentation API](https://memu.pro/docs)
- 💬 [Communauté Discord](https://discord.gg/memu)

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

</div>

---

## 🤝 Comment Contribuer

Nous accueillons les contributions de la communauté! Que vous corrigiez des bugs, ajoutiez des fonctionnalités ou amélioriez la documentation, votre aide est appréciée.

### Pour Commencer

Pour commencer à contribuer à MemU, vous devrez configurer votre environnement de développement:

#### Prérequis
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (gestionnaire de paquets Python)
- Git

#### Configurer l'Environnement de Développement
```bash
# 1. Fork et cloner le dépôt
git clone https://github.com/YOUR_USERNAME/memU.git
cd memU

# 2. Installer les dépendances de développement
make install
```

La commande `make install` va:
- Créer un environnement virtuel en utilisant `uv`
- Installer toutes les dépendances du projet
- Configurer les hooks pre-commit pour les vérifications de qualité de code

#### Exécuter les Vérifications de Qualité

Avant de soumettre votre contribution, assurez-vous que votre code passe toutes les vérifications de qualité:
```bash
make check
```

La commande `make check` exécute:
- **Vérification du fichier lock**: Assure la cohérence de `pyproject.toml`
- **Hooks pre-commit**: Lint le code avec Ruff, formate avec Black
- **Vérification de types**: Exécute `mypy` pour l'analyse de types statiques
- **Analyse de dépendances**: Utilise `deptry` pour trouver les dépendances obsolètes

### Directives de Contribution

Pour des directives de contribution détaillées, standards de code et pratiques de développement, voir [CONTRIBUTING.md](../CONTRIBUTING.md).

**Conseils rapides:**
- Créer une nouvelle branche pour chaque fonctionnalité ou correction de bug
- Écrire des messages de commit clairs
- Ajouter des tests pour les nouvelles fonctionnalités
- Mettre à jour la documentation si nécessaire
- Exécuter `make check` avant de pousser

---

## 📄 Licence

[Apache License 2.0](../LICENSE.txt)

---

## 🌍 Communauté

- **GitHub Issues**: [Signaler des bugs & demander des fonctionnalités](https://github.com/NevaMind-AI/MemU/issues)
- **Discord**: [Rejoindre la communauté](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter)**: [Suivre @memU_ai](https://x.com/memU_ai)
- **Contact**: info@nevamind.ai

---

<div align="center">

⭐ **Mettez-nous une étoile sur GitHub** pour être notifié des nouvelles versions!

</div>
