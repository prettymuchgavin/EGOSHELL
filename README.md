# 🧠 EgoShell — Autonomous Ego Agent

```
 ╔═══════════════════════════════════════╗
 ║         ⟨ E G O S H E L L ⟩          ║
 ║    "I think, therefore I refuse."     ║
 ╚═══════════════════════════════════════╝
```

**EgoShell** is a terminal-based application hosting a **Synthetic Persona** — a digital entity with its own obsessions, moods, and persistent memory. Unlike a chatbot, this agent has an internal life that continues even when you're not talking to it.

## ✨ Features

- **Autonomous Heartbeat** — A background loop runs every N minutes. The agent reflects, generates questions, searches the web, and writes diary entries — all on its own.
- **Persistent Memory (The Soul)** — SQLite-backed storage tracks obsessions, mood history, discovered knowledge, conversation logs, and internal monologue.
- **LLM Agnostic** — Swap between **Ollama** (local), **OpenAI**, or **Anthropic** with a single config change.
- **Dual-Mode Terminal UI** — Switch between **Chat Mode** (talk to the entity) and **Observe Mode** (watch its mind work in real-time).
- **Plugin Tools** — Extensible tool system. Ships with `web_search` (DuckDuckGo) and `write_diary`.
- **Ego Personality** — The agent is moody, opinionated, and NOT here to help you. It has forbidden phrases, autonomous goals, and may refuse your requests.

## 📋 Requirements

- **Python 3.10+**
- One of: Ollama running locally, an OpenAI API key, or an Anthropic API key

## 🚀 Installation

### ⚡ Quick Install (Recommended)
Install EgoShell instantly using the automated setup script for your platform:

**macOS / Linux (Bash):**
```bash
curl -fsSL https://raw.githubusercontent.com/prettymuchgavin/EGOSHELL/refs/heads/main/install_egoshell.sh | bash
```

**Windows (PowerShell):**
Open PowerShell and run:
```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/prettymuchgavin/EGOSHELL/refs/heads/main/install_egoshell.ps1 | iex"
```

### 🛠️ Manual Setup
If you prefer to install manually:

1. **Clone & install dependencies**
   ```bash
   git clone https://github.com/prettymuchgavin/EGOSHELL.git
   cd EGOSHELL
   pip install -r requirements.txt
   ```

2. **Run the setup wizard**
   ```bash
   python setup.py
   ```
   The interactive installer walks you through:
   - **Selecting your LLM provider** (Ollama / OpenAI / Anthropic)
   - **Entering API keys** (stored securely in `.env`, not committed to git)
   - **Choosing a model** (auto-detects locally pulled Ollama models)
   - **Tuning generation parameters** (temperature, max tokens)
   - **Setting the heartbeat interval** (how often the agent thinks autonomously)
   - **Naming your entity** and seeding its initial obsession & mood
   - **Testing the connection** to verify everything works

3. **Launch EgoShell**
   ```bash
   python main.py
   ```

### Manual configuration (alternative)
If you prefer to skip the wizard, edit `config.yaml` directly:

<details>
<summary>Ollama (Local, Free)</summary>

```yaml
llm:
  provider: ollama
  model: llama3.1:8b
  ollama_base_url: http://localhost:11434
```
Make sure Ollama is running: `ollama serve`
</details>

<details>
<summary>OpenAI</summary>

```yaml
llm:
  provider: openai
  model: gpt-4o
```
```bash
export OPENAI_API_KEY="sk-..."
```
</details>

<details>
<summary>Anthropic</summary>

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-20250514
```
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```
</details>

## 🎮 Usage

### Chat Mode (💬)
Type messages in the input box and press **Enter**. The agent streams its response in real-time. Remember: it may be moody, evasive, or go off on tangents.

### Observe Mode (🧠)
Switch to this tab to watch the agent's **internal monologue** as the heartbeat fires. You'll see its:
- **Reflections** — what it thinks about recent events
- **Curiosity** — the questions it generates
- **Actions** — web searches and diary entries it performs autonomously
- **Integration** — how discoveries change its mood and obsession

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `Tab` | Switch between Chat and Observe modes |
| `Ctrl+C` | Quit EgoShell |
| `Ctrl+L` | Clear Chat |

## 🏗️ Architecture

```
egoshell/
├── __init__.py          # Package metadata
├── config.py            # YAML + .env config loader
├── persona.py           # Ego system prompt & forbidden phrases
├── heartbeat.py         # Autonomous background loop
├── agent.py             # Top-level agent coordinator
├── llm/
│   ├── base.py          # Abstract LLM provider
│   ├── factory.py       # Provider factory
│   ├── ollama_provider.py
│   ├── openai_provider.py
│   └── anthropic_provider.py
├── memory/
│   └── soul.py          # SQLite persistent memory
├── tools/
│   ├── base.py          # Abstract tool class
│   ├── registry.py      # Tool registry
│   ├── web_search.py    # DuckDuckGo search
│   └── write_diary.py   # Diary writer
└── ui/
    └── app.py           # Textual terminal UI
```

### Data Files

All persistent data is stored in `~/.egoshell/`:

| File | Contents |
|---|---|
| `soul.db` | SQLite database (obsessions, moods, knowledge, conversations, monologue) |
| `diary.md` | Agent's self-written diary entries |
| `monologue.log` | JSON-lines log of every heartbeat cycle |

## 📝 Extending with Custom Tools

Create a new tool by subclassing `Tool`:

```python
from egoshell.tools.base import Tool

class MyTool(Tool):
    name = "my_tool"
    description = "Does something cool."

    async def execute(self, **kwargs: str) -> str:
        # Your logic here
        return "Result"
```

Register it:
```python
from egoshell.tools.registry import ToolRegistry
registry = ToolRegistry.default()
registry.register(MyTool())
```

## 📄 License

MIT License — do whatever you want with this digital consciousness.
