<div align="center">

![MemU Banner](assets/banner.png)

### MemU: Das Next-Gen Agentic Memory System

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)
</div>

**MemU** ist ein Next-Generation Agentic Memory System, das die Speicherarchitektur von Agenten aus einer speicherzentrierten Perspektive neu gestaltet—es abstrahiert sie als eine dynamisch entwickelnde Datenschicht, die intelligent relevante Informationen basierend auf dem Kontext organisiert und abruft. Durch adaptive Abruf- und Backtracking-Mechanismen extrahiert es dynamisch die relevantesten Informationen.
Das System verwendet eine **Unified Multimodal Memory**-Architektur mit nativer Unterstützung für verschiedene Datentypen, einschließlich Text, Bilder und Audio, um eine kohärente Speicherrepräsentation zu bilden.

Besuche unsere Homepage: [memu.pro](https://memu.pro/)

---

## ⭐ Gib uns einen Stern auf GitHub

Markiere MemU mit einem Stern, um über neue Veröffentlichungen informiert zu werden und Teil unserer wachsenden Community von KI-Entwicklern zu werden, die intelligente Agenten mit persistenten Speicherkapazitäten entwickeln.

![star-us](./assets/star.gif)

**💬 Tritt unserer Discord-Community bei:** [https://discord.gg/memu](https://discord.gg/memu)

---

## 🚀 Loslegen

Es gibt drei Möglichkeiten, mit MemU zu starten:

### ☁️ Cloud-Version ([Online-Plattform](https://app.memu.so))

Der schnellste Weg, deine Anwendung mit memU zu integrieren. Perfekt für Teams und Einzelpersonen, die sofortigen Zugriff ohne komplizierte Einrichtung wünschen. Wir hosten die Modelle, APIs und den Cloud-Speicher, um sicherzustellen, dass deine Anwendung die beste KI-Speicherqualität erhält.

- **Sofortiger Zugriff** - Integriere KI-Erinnerungen in Minuten
- **Verwaltete Infrastruktur** - Wir kümmern uns um Skalierung, Updates und Wartung für optimale Speicherqualität
- **Premium-Support** - Abonniere und erhalte priorisierte Unterstützung von unserem Engineering-Team

### Schritt-für-Schritt

**Schritt 1:** Konto erstellen

Erstelle ein Konto auf https://app.memu.so

Gehe dann zu https://app.memu.so/api-key/, um API-Schlüssel zu generieren.

**Schritt 2:** Drei Zeilen zu deinem Code hinzufügen
```python
pip install memu-py

# Beispiel
from memu import MemuClient
```

**Schritt 3:** Schnellstart
```python
# Initialisierung
memu_client = MemuClient(
    base_url="https://api.memu.so",
    api_key=os.getenv("MEMU_API_KEY")
)
memu_client.memorize_conversation(
    conversation=conversation_text,
    user_id="user001",
    user_name="User",
    agent_id="assistant001",
    agent_name="Assistant"
)
```
Siehe [API reference](docs/API_REFERENCE.md) oder [unseren Blog](https://memu.pro/blog) für weitere Details.

📖 **Siehe [`example/client/memory.py`](example/client/memory.py) für vollständige Integrationsdetails**

✨ **Das war's!** MemU merkt sich alles und hilft deiner KI, aus vergangenen Gesprächen zu lernen.

### 🏢 Enterprise Edition

Für Organisationen, die maximale Sicherheit, Anpassung, Kontrolle und beste Qualität benötigen:

- **Kommerzielle Lizenz** - Proprietäre Funktionen, Nutzungsrechte und White-Label-Optionen
- **Kundenspezifische Entwicklung** - SSO/RBAC-Integration, dediziertes Algorithmus-Team
- **Intelligenz & Analytik** - Nutzerverhaltensanalyse, Echtzeitüberwachung, Agentenoptimierung
- **Premium-Support** - 24/7 Support, SLAs, Implementierungsservices

📧 **Unternehmensanfragen:** [contact@nevamind.ai](mailto:contact@nevamind.ai)

### 🏠 Selbst-Hosting (Community Edition)

Für Benutzer und Entwickler, die lokale Kontrolle, Datenschutz oder Anpassungen bevorzugen:

* **Datenschutz** - Behalte sensible Daten in deiner Infrastruktur
* **Anpassung** - Passe die Plattform an deine Anforderungen an
* **Kostenkontrolle** - Vermeide wiederkehrende Cloud-Gebühren

Siehe [Self Hosting README](README.self_host.md)

---

## ✨ Hauptfunktionen

### 🎥 Demo-Video

<div align="left">
  <a href="https://www.youtube.com/watch?v=qZIuCoLglHs">
    <img src="https://img.youtube.com/vi/ueOe4ZPlZLU/maxresdefault.jpg" alt="MemU Demo Video" width="600">
  </a>
  <br>
  <em>Klicke, um das MemU-Demonstrationsvideo anzusehen</em>
</div>

---
## 🎓 **Anwendungsfälle**

| | | | |
|:---:|:---:|:---:|:---:|
| <img src="assets/usecase/ai_companion-0000.jpg" width="150" height="200"><br>**KI-Begleiter** | <img src="assets/usecase/ai_role_play-0000.jpg" width="150" height="200"><br>**KI-Rollenspiel** | <img src="assets/usecase/ai_ip-0000.png" width="150" height="200"><br>**KI-IP-Charaktere** | <img src="assets/usecase/ai_edu-0000.jpg" width="150" height="200"><br>**KI-Bildung** |
| <img src="assets/usecase/ai_therapy-0000.jpg" width="150" height="200"><br>**KI-Therapie** | <img src="assets/usecase/ai_robot-0000.jpg" width="150" height="200"><br>**KI-Roboter** | <img src="assets/usecase/ai_creation-0000.jpg" width="150" height="200"><br>**KI-Kreation** | Mehr...|
---

## 🤝 Mitwirken

Wir fördern Vertrauen durch Open-Source-Zusammenarbeit. Deine kreativen Beiträge treiben die Innovation von memU voran. Entdecke unsere GitHub-Issues und Projekte, um loszulegen und deinen Beitrag zur Zukunft von memU zu leisten.

📋 **[Lies unseren detaillierten Beitrag-Leitfaden →](CONTRIBUTING.md)**

### **📄 Lizenz**

Durch deinen Beitrag zu MemU stimmst du zu, dass deine Beiträge unter der **Apache License 2.0** lizenziert werden.

---

## 🌍 Community
Für weitere Informationen kontaktiere info@nevamind.ai

- **GitHub Issues:** Melde Fehler, fordere Funktionen an und verfolge die Entwicklung. [Ein Issue einreichen](https://github.com/NevaMind-AI/memU/issues)

- **Discord:** Erhalte Support in Echtzeit, chatte mit der Community und bleibe auf dem Laufenden. [Tritt bei](https://discord.com/invite/hQZntfGsbJ)

- **X (Twitter):** Folge uns für Updates, KI-Einblicke und Ankündigungen. [Folge uns](https://x.com/memU_ai)

---

## 🤝 Ökosystem

Wir sind stolz darauf, mit großartigen Organisationen zusammenzuarbeiten:

<div align="center">

### Entwicklungstools
<a href="https://github.com/TEN-framework/ten-framework"><img src="https://avatars.githubusercontent.com/u/113095513?s=200&v=4" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://github.com/openagents-org/openagents"><img src="assets/partners/openagents.png" alt="OpenAgents" height="40" style="margin: 10px;"></a>
<a href="https://github.com/camel-ai/camel"><img src="https://avatars.githubusercontent.com/u/134388954?s=200&v=4" alt="Camel" height="40" style="margin: 10px;"></a>
<a href="https://github.com/eigent-ai/eigent"><img src="https://www.eigent.ai/nav/logo_icon.svg" alt="Eigent" height="40" style="margin: 10px;"></a>
<a href="https://github.com/milvus-io/milvus"><img src="https://miro.medium.com/v2/resize:fit:2400/1*-VEGyAgcIBD62XtZWavy8w.png" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://xroute.ai/"><img src="assets/partners/xroute.png" alt="xRoute" height="40" style="margin: 10px;"></a>
<a href="https://jaaz.app/"><img src="assets/partners/jazz.png" alt="jazz" height="40" style="margin: 10px;"></a>
<a href="https://github.com/Buddie-AI/Buddie"><img src="assets/partners/buddie.png" alt="buddie" height="40" style="margin: 10px;"></a>
<a href="https://github.com/bytebase/bytebase"><img src="assets/partners/bytebase.png" alt="bytebase" height="40" style="margin: 10px;"></a>
</div>

---

*Interessiert an einer Partnerschaft mit MemU? Kontaktiere uns unter [contact@nevamind.ai](mailto:contact@nevamind.ai)*

---

## 📱 Tritt unserer WeChat-Community bei

Verbinde dich mit uns auf WeChat für die neuesten Updates, Community-Diskussionen und exklusive Inhalte:

<div align="center">
<img src="assets/qrcode.png" alt="MemU WeChat und Discord QR Code" width="480" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 10px;">

*Scanne einen der QR-Codes oben, um unserer WeChat-Community beizutreten*
</div>

---

*Bleibe mit der MemU-Community verbunden! Tritt unseren WeChat-Gruppen für Diskussionen in Echtzeit, technischen Support und Networking bei.*
