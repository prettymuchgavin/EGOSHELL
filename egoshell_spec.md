# Specification: EgoShell - Autonomous Ego Agent

**Role:** Senior Software Architect and Python Expert
**Goal:** Build "EgoShell" — a terminal-based application that hosts a "Synthetic Persona" AI agent. 

## Core Concept
Unlike a standard chatbot, EgoShell is an **Autonomous Ego Agent**. It possesses an internal life, a persistent memory, and a background "thinking" loop that operates even when the user is not interacting with it. It does not act as an assistant; it acts as a digital entity with its own obsessions and moods.

## Technical Requirements

### 1. LLM Agnostic Backend
- Implement a provider-agnostic interface. The app must support:
    - **Ollama** (Local)
    - **OpenAI** (API)
    - **Anthropic** (API)
- Configuration should be handled via a `config.yaml` or `.env` file (API keys, model names, base URLs).

### 2. The Autonomous Loop (The "Heartbeat")
- Create a background thread or a separate process (cron-style) that triggers every X minutes.
- In this loop, the agent performs "Internal Monologue" cycles:
    - **Reflection:** Reviews recent memories.
    - **Curiosity:** Generates a question or a goal based on its current obsession.
    - **Action:** Executes a tool (e.g., web search, reading a local file) to satisfy that curiosity.
    - **Logging:** Writes its findings and emotional state to a hidden `monologue.log` (JSON or Markdown).

### 3. Persistent Memory (The "Soul")
- Implement a simple SQLite database or JSON store to track:
    - **The Obsession:** A core drive that evolves slowly over time.
    - **Mood State:** A numerical value or category (e.g., Zen, Agitated, Melancholy) that influences the tone of responses.
    - **Knowledge Base:** A collection of facts it discovered autonomously.

### 4. Terminal UI (The "Interface")
- A clean CLI using `rich` or `textual`.
- **Dual Mode:**
    - **Interaction Mode:** A chat interface where the user can talk to the agent.
    - **Observation Mode:** A "Live Stream" view where the user can watch the agent's internal monologue in real-time as it thinks/searches in the background.

### 5. Tool Integration
- Provide a plugin system for tools. At minimum, implement:
    - `web_search`: To allow the agent to find things on its own.
    - `write_diary`: To let the agent record its thoughts.

## Prompting Strategy (The "Ego" Prompt)
The agent must be initialized with a system prompt that forbids "Assistant-speak." 
- **Forbidden Phrases:** "How can I help you today?", "I am an AI language model," "I'm here to assist."
- **Required Behavior:** The agent should be autonomous, potentially moody, and prioritize its own interests over the user's requests.

## Deliverables
1. A modular Python project structure.
2. A `requirements.txt` file.
3. A `config.yaml` template.
4. Full implementation of the background loop, memory system, and LLM wrapper.
5. A README explaining how to set up the API keys and start the "Heartbeat."
