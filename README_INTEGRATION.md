# MemU + OpenClaw Integration

This project implements a complete integration between the **MemU memory framework** and **OpenClaw**, creating a proactive memory system for AI agents. The integration allows OpenClaw to maintain persistent, searchable memories through the MemU framework.

## 🌟 Overview

The integration consists of:
- **MemU Memory Framework**: Advanced memory management for AI agents
- **OpenClaw Bridge**: Translation layer between OpenClaw and MemU APIs
- **Legacy Memory Import**: Migration of existing Clawd-AI-Assistant memories
- **Proactive Monitoring**: Continuous memory extraction from OpenClaw interactions
- **Persistent State**: Long-term memory retention across sessions

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   OpenClaw      │◄──►│  Bridge Server   │◄──►│   MemU Core     │
│   (AI Agent)    │    │  (port 5000)     │    │  (Memory DB)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
       │                       │                        │
       │              ┌──────────────────┐              │
       └─────────────►│  Memory Flow     │◄─────────────┘
                      │  (Automatic)     │
                      └──────────────────┘
```

### Components

1. **OpenClaw Bridge (`openclaw_bridge.py`)**: 
   - Exposes OpenAI-compatible API endpoints
   - Translates API calls to OpenClaw operations
   - Handles memory extraction and storage requests

2. **Memory Service (`config.py`)**:
   - Configures MemU with OpenClaw bridge as LLM provider
   - Defines memory categories and extraction rules
   - Manages persistent memory storage

3. **Legacy Import (`import_legacy.py`)**:
   - Imports existing memories from Clawd-AI-Assistant
   - Converts legacy format to MemU-compatible format
   - Preserves historical context

4. **Management Scripts (`manager.py`)**:
   - Controls the complete integration lifecycle
   - Starts/stops services
   - Validates setup
   - Generates reports

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- Node.js (for OpenClaw)
- OpenClaw properly installed at `C:\Users\16663\Desktop\openclaw\`

### Installation

1. Clone the repository:
```bash
cd C:\Users\16663\Desktop\openclaw\memU
```

2. Install dependencies:
```bash
pip install -e .
```

3. Verify OpenClaw installation:
```bash
node C:\Users\16663\Desktop\openclaw\openclaw.mjs --version
```

### Basic Usage

1. **Setup the complete environment**:
```bash
python manager.py setup
```

2. **Start the bridge service**:
```bash
python manager.py start
```

3. **Import legacy memories**:
```bash
python manager.py import
```

4. **Validate the setup**:
```bash
python manager.py validate
```

5. **Monitor continuously** (in background):
```bash
python manager.py monitor
```

6. **Generate reports**:
```bash
python manager.py report
```

## 🔧 Configuration

The system is configured via `config.py` which defines:

- **Database settings**: Currently using in-memory storage (can be switched to PostgreSQL)
- **LLM profiles**: Pointing to the OpenClaw bridge service
- **Memory categories**: Predefined categories for organizing memories
- **Proactive settings**: Scan intervals and retention policies

### Environment Variables

While the bridge uses dummy credentials, you may want to set:

```bash
# For PostgreSQL backend (optional)
export MEMU_DATABASE_URL="postgresql://user:pass@localhost/dbname"
export MEMU_VECTOR_URL="postgresql://user:pass@localhost/dbname"
```

## 📊 Memory Categories

The system automatically categorizes memories into:

- `personal_info`: Personal information and user preferences
- `preferences`: Likes, dislikes, and behavioral patterns
- `relationships`: Information about people and entities
- `activities`: Hobbies, interests, and daily routines
- `goals`: Objectives, plans, and aspirations
- `experiences`: Past events and memorable moments
- `knowledge`: Facts, expertise, and learned information
- `opinions`: Viewpoints, beliefs, and perspectives
- `habits`: Regular behaviors and routines
- `work_life`: Professional information and career
- `hle_analysis`: HLE challenge analyses and solutions
- `system_operations`: System operations and autonomous behavior
- `autonomous_behavior`: Self-modifications and proactive actions

## 🧠 Proactive Memory

The system implements proactive memory management:

- **Continuous Monitoring**: Scans OpenClaw interactions every 5 minutes
- **Automatic Extraction**: Identifies and extracts relevant memories
- **Smart Categorization**: Assigns memories to appropriate categories
- **Context Assembly**: Prepares relevant context for future interactions
- **Self-Improvement**: Learns from interactions to improve memory quality

## 📈 HLE Challenge Integration

The system includes special handling for HLE (Holistic Language Education) challenge data:

- Imported from legacy Clawd-AI-Assistant diary entries
- Specialized category for mathematical and logical analyses
- Cross-referencing between problems and solutions
- Pattern recognition across different problem domains

## 🛠️ Management Commands

The `manager.py` script provides several commands:

- `start`: Start the OpenClaw bridge service
- `stop`: Stop the bridge service
- `import`: Import legacy memories
- `validate`: Validate the complete setup
- `monitor`: Start continuous monitoring
- `report`: Generate memory reports
- `setup`: Complete environment setup
- `all`: Run complete sequence of operations

## 🚨 Troubleshooting

### Common Issues

1. **Bridge not responding**: Ensure OpenClaw is properly installed and accessible
2. **Memory import failures**: Check that legacy files exist at expected paths
3. **Validation errors**: Verify that the bridge service is running on port 5000

### Logs

- Bridge service logs: `logs/bridge_service.log`
- Debug logs: `bridge_debug.log`
- Application logs: Generated in `logs/` directory

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.

## 🌐 Community

For support and discussions about MemU:
- GitHub: [NevaMind-AI/memU](https://github.com/NevaMind-AI/memU)
- Discord: [Join the community](https://discord.gg/memu)
- Twitter: [@memU_ai](https://x.com/memU_ai)

For OpenClaw:
- GitHub: [openclaw](https://github.com/openclaw/openclaw)
- Discord: [OpenClaw Community](https://discord.com/invite/clawd)