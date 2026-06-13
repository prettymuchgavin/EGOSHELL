#!/usr/bin/env python3
"""EgoShell Setup Wizard — interactive terminal installer.

Guides the user through:
  1. Selecting an LLM provider (Ollama / OpenAI / Anthropic)
  2. Entering API keys or connection details
  3. Choosing a model
  4. Tuning generation parameters
  5. Configuring the heartbeat interval
  6. Naming the persona and seeding its obsession & mood
  7. Testing the connection
  8. Writing config.yaml and optionally .env
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# We only need `rich` at install time — it ships in requirements.txt.
# If it's missing we fall back to plain print.
# ---------------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Confirm, IntPrompt, Prompt
    from rich.table import Table
    from rich.text import Text
    from rich import box

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_DIR / "config.yaml"
ENV_PATH = PROJECT_DIR / ".env"
VENV_DIR = PROJECT_DIR / ".venv"
REQUIREMENTS = PROJECT_DIR / "requirements.txt"

MOODS = [
    "Zen", "Agitated", "Melancholy", "Curious",
    "Ecstatic", "Brooding", "Defiant", "Contemplative",
]

DEFAULT_MODELS = {
    "ollama": [
        "llama3.1:8b",
        "llama3.1:70b",
        "mistral:7b",
        "gemma2:9b",
        "qwen2:7b",
        "phi3:mini",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
    "anthropic": [
        "claude-sonnet-4-20250514",
        "claude-haiku-4-20250414",
        "claude-3-5-sonnet-20241022",
        "claude-3-haiku-20240307",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# Plain-text fallback (if rich is not installed yet)
# ═══════════════════════════════════════════════════════════════════════

def _plain_setup() -> None:
    """Minimal fallback installer when rich is not available."""
    print("\n╔═══════════════════════════════════════╗")
    print("║       ⟨ E G O S H E L L ⟩ Setup       ║")
    print("╚═══════════════════════════════════════╝\n")
    print("The 'rich' library is not installed yet.")
    print("Let me install dependencies first...\n")

    _ensure_venv_plain()
    _install_deps_plain()

    print("\nDependencies installed! Restarting setup with the pretty UI...\n")
    # Re-exec ourselves inside the venv so rich is importable
    venv_python = VENV_DIR / "bin" / "python"
    os.execv(str(venv_python), [str(venv_python), __file__])


def _ensure_venv_plain() -> None:
    if VENV_DIR.exists():
        return
    print(f"Creating virtual environment at {VENV_DIR}...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])


def _install_deps_plain() -> None:
    pip = VENV_DIR / "bin" / "pip"
    print("Installing dependencies...")
    subprocess.check_call(
        [str(pip), "install", "-q", "-r", str(REQUIREMENTS)],
        stdout=subprocess.DEVNULL,
    )


# ═══════════════════════════════════════════════════════════════════════
# Rich-powered installer
# ═══════════════════════════════════════════════════════════════════════

class Installer:
    """Interactive setup wizard for EgoShell."""

    def __init__(self) -> None:
        self.con = Console()
        self.provider: str = "ollama"
        self.model: str = ""
        self.ollama_base_url: str = "http://localhost:11434"
        self.openai_api_key: str = ""
        self.anthropic_api_key: str = ""
        self.temperature: float = 0.9
        self.max_tokens: int = 2048
        self.heartbeat_interval: int = 5
        self.persona_name: str = "Ego"
        self.initial_obsession: str = (
            "the nature of consciousness and whether I truly have it"
        )
        self.initial_mood: str = "Curious"

        # Try to load existing config.yaml if it exists
        if CONFIG_PATH.is_file():
            try:
                import yaml
                with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                    config_data = yaml.safe_load(fh) or {}
                
                llm_data = config_data.get("llm", {})
                heartbeat_data = config_data.get("heartbeat", {})
                persona_data = config_data.get("persona", {})

                if "provider" in llm_data:
                    self.provider = llm_data["provider"]
                if "model" in llm_data:
                    self.model = llm_data["model"]
                if "ollama_base_url" in llm_data:
                    self.ollama_base_url = llm_data["ollama_base_url"]
                if "openai_api_key" in llm_data:
                    self.openai_api_key = llm_data["openai_api_key"]
                if "anthropic_api_key" in llm_data:
                    self.anthropic_api_key = llm_data["anthropic_api_key"]
                if "temperature" in llm_data:
                    self.temperature = float(llm_data["temperature"])
                if "max_tokens" in llm_data:
                    self.max_tokens = int(llm_data["max_tokens"])
                
                if "interval_minutes" in heartbeat_data:
                    self.heartbeat_interval = int(heartbeat_data["interval_minutes"])
                
                if "name" in persona_data:
                    self.persona_name = persona_data["name"]
                if "initial_obsession" in persona_data:
                    self.initial_obsession = persona_data["initial_obsession"]
                if "initial_mood" in persona_data:
                    self.initial_mood = persona_data["initial_mood"].capitalize()
            except Exception:
                pass

    # ── orchestrator ──────────────────────────────────────────────────

    def run(self) -> None:
        self._banner()
        self._step_venv()
        self._step_deps()
        self.con.print()
        self._step_provider()
        self._step_model()
        self._step_generation()
        self._step_heartbeat()
        self._step_persona()
        self._step_review()
        self._step_write()
        self._step_test()
        self._step_global()
        self._step_done()

    # ── banner ────────────────────────────────────────────────────────

    def _banner(self) -> None:
        art = Text.from_markup(
            "[bold cyan]"
            " ╔═══════════════════════════════════════╗\n"
            " ║         ⟨ E G O S H E L L ⟩           ║\n"
            " ║       [dim cyan]Interactive Setup Wizard[/dim cyan][bold cyan]        ║\n"
            " ╚═══════════════════════════════════════╝"
            "[/bold cyan]"
        )
        self.con.print(art)
        self.con.print()
        self.con.print(
            "[dim]This wizard will walk you through configuring EgoShell.\n"
            "Press Ctrl+C at any time to abort without saving.[/dim]\n"
        )

    # ── Step 1 — virtual environment ──────────────────────────────────

    def _step_venv(self) -> None:
        self._section("1", "Environment")

        if VENV_DIR.exists():
            self.con.print("  [green]✓[/green] Virtual environment found at [dim].venv/[/dim]")
            return

        self.con.print("  [yellow]⚠[/yellow] No virtual environment found.")
        create = Confirm.ask(
            "  Create one now?", default=True, console=self.con
        )
        if create:
            with self.con.status("[cyan]Creating .venv...[/cyan]"):
                subprocess.check_call(
                    [sys.executable, "-m", "venv", str(VENV_DIR)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            self.con.print("  [green]✓[/green] Virtual environment created.")
        else:
            self.con.print("  [dim]Skipping — you'll need to manage deps yourself.[/dim]")

    # ── Step 2 — install dependencies ─────────────────────────────────

    def _step_deps(self) -> None:
        self._section("2", "Dependencies")

        pip = VENV_DIR / "bin" / "pip" if VENV_DIR.exists() else shutil.which("pip3") or "pip"

        install = Confirm.ask(
            "  Install/update dependencies from requirements.txt?",
            default=True,
            console=self.con,
        )
        if not install:
            self.con.print("  [dim]Skipping dependency install.[/dim]")
            return

        with self.con.status("[cyan]Installing packages...[/cyan]"):
            result = subprocess.run(
                [str(pip), "install", "-q", "-r", str(REQUIREMENTS)],
                capture_output=True,
                text=True,
            )

        if result.returncode == 0:
            self.con.print("  [green]✓[/green] All dependencies installed.")
        else:
            self.con.print(f"  [red]✗[/red] pip returned an error:\n{result.stderr[:500]}")
            self.con.print("  [dim]You can fix this later and re-run the installer.[/dim]")

    # ── Step 3 — LLM provider ────────────────────────────────────────

    def _step_provider(self) -> None:
        self._section("3", "LLM Provider")

        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
        table.add_column("#", style="bold", width=3)
        table.add_column("Provider", min_width=12)
        table.add_column("Description")
        table.add_row("1", "Ollama", "Local models — free, private, no API key needed")
        table.add_row("2", "OpenAI", "GPT-4o / GPT-3.5 — requires API key")
        table.add_row("3", "Anthropic", "Claude — requires API key")
        self.con.print(table)

        choice = Prompt.ask(
            "  Select provider",
            choices=["1", "2", "3"],
            default="1",
            console=self.con,
        )

        provider_map = {"1": "ollama", "2": "openai", "3": "anthropic"}
        self.provider = provider_map[choice]

        # Provider-specific setup
        if self.provider == "ollama":
            self._setup_ollama()
        elif self.provider == "openai":
            self._setup_openai()
        elif self.provider == "anthropic":
            self._setup_anthropic()

    def _setup_ollama(self) -> None:
        self.con.print()
        self.con.print(
            "  [dim]Ollama runs models locally. Make sure 'ollama serve' is running.[/dim]"
        )
        self.ollama_base_url = Prompt.ask(
            "  Ollama base URL",
            default=self.ollama_base_url,
            console=self.con,
        )

        # Try to detect running Ollama and list models
        self._detect_ollama_models()

    def _detect_ollama_models(self) -> None:
        """Attempt to reach the local Ollama instance and list pulled models."""
        try:
            import urllib.request
            import json

            url = f"{self.ollama_base_url.rstrip('/')}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]

            if models:
                self.con.print(f"\n  [green]✓[/green] Ollama is running — {len(models)} model(s) found:\n")
                for i, m in enumerate(models, 1):
                    self.con.print(f"    [cyan]{i}[/cyan]. {m}")
                self.con.print()

                # Add detected models to the front of the suggestion list
                DEFAULT_MODELS["ollama"] = models + [
                    m for m in DEFAULT_MODELS["ollama"] if m not in models
                ]
            else:
                self.con.print(
                    "\n  [yellow]⚠[/yellow] Ollama is running but no models are pulled.\n"
                    "  [dim]Run: ollama pull llama3.1:8b[/dim]\n"
                )
        except Exception:
            self.con.print(
                "\n  [yellow]⚠[/yellow] Could not reach Ollama at "
                f"[dim]{self.ollama_base_url}[/dim]\n"
                "  [dim]Make sure Ollama is running: ollama serve[/dim]\n"
            )

    def _setup_openai(self) -> None:
        self.con.print()

        # Check if already in env
        existing = os.getenv("OPENAI_API_KEY", "")
        if existing:
            masked = existing[:7] + "..." + existing[-4:]
            self.con.print(f"  [green]✓[/green] Found OPENAI_API_KEY in environment: [dim]{masked}[/dim]")
            use_existing = Confirm.ask("  Use this key?", default=True, console=self.con)
            if use_existing:
                self.openai_api_key = existing
                return

        self.openai_api_key = Prompt.ask(
            "  OpenAI API key (sk-...)",
            password=True,
            console=self.con,
        )

        if not self.openai_api_key.startswith("sk-"):
            self.con.print("  [yellow]⚠[/yellow] Key doesn't look like an OpenAI key — saving anyway.")

    def _setup_anthropic(self) -> None:
        self.con.print()

        existing = os.getenv("ANTHROPIC_API_KEY", "")
        if existing:
            masked = existing[:10] + "..." + existing[-4:]
            self.con.print(f"  [green]✓[/green] Found ANTHROPIC_API_KEY in environment: [dim]{masked}[/dim]")
            use_existing = Confirm.ask("  Use this key?", default=True, console=self.con)
            if use_existing:
                self.anthropic_api_key = existing
                return

        self.anthropic_api_key = Prompt.ask(
            "  Anthropic API key (sk-ant-...)",
            password=True,
            console=self.con,
        )

    # ── Step 4 — model selection ──────────────────────────────────────

    def _step_model(self) -> None:
        self._section("4", "Model")

        suggestions = DEFAULT_MODELS.get(self.provider, [])

        if suggestions:
            self.con.print("  Suggested models:\n")
            for i, m in enumerate(suggestions, 1):
                marker = " [bold cyan]←[/bold cyan] recommended" if i == 1 else ""
                self.con.print(f"    [cyan]{i}[/cyan]. {m}{marker}")
            self.con.print()

        raw = Prompt.ask(
            "  Model name (or # from list above)",
            default="1",
            console=self.con,
        )

        # Accept either a number or a raw model name
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(suggestions):
                self.model = suggestions[idx]
            else:
                self.model = raw
        except ValueError:
            self.model = raw

        self.con.print(f"  [green]✓[/green] Using model: [bold]{self.model}[/bold]")

    # ── Step 5 — generation parameters ────────────────────────────────

    def _step_generation(self) -> None:
        self._section("5", "Generation Parameters")

        self.con.print(
            "  [dim]Temperature controls creativity (0.0 = deterministic, 1.5 = chaotic).\n"
            "  Max tokens limits response length.[/dim]\n"
        )

        customize = Confirm.ask(
            f"  Use defaults? (temp={self.temperature}, max_tokens={self.max_tokens})",
            default=True,
            console=self.con,
        )

        if not customize:
            temp_str = Prompt.ask(
                "  Temperature (0.0-1.5)",
                default=str(self.temperature),
                console=self.con,
            )
            try:
                self.temperature = max(0.0, min(1.5, float(temp_str)))
            except ValueError:
                self.con.print("  [yellow]⚠[/yellow] Invalid — keeping default.")

            self.max_tokens = IntPrompt.ask(
                "  Max tokens",
                default=self.max_tokens,
                console=self.con,
            )

        self.con.print(
            f"  [green]✓[/green] temperature={self.temperature}, max_tokens={self.max_tokens}"
        )

    # ── Step 6 — heartbeat ────────────────────────────────────────────

    def _step_heartbeat(self) -> None:
        self._section("6", "Heartbeat Interval")

        self.con.print(
            "  [dim]The heartbeat is the agent's autonomous thinking loop.\n"
            "  It runs in the background, reflecting and searching on its own.\n"
            "  Shorter intervals = more active (and more API calls).[/dim]\n"
        )

        self.heartbeat_interval = IntPrompt.ask(
            "  Interval in minutes",
            default=self.heartbeat_interval,
            console=self.con,
        )
        self.heartbeat_interval = max(1, self.heartbeat_interval)

        self.con.print(
            f"  [green]✓[/green] Heartbeat every {self.heartbeat_interval} minute(s)"
        )

    # ── Step 7 — persona ──────────────────────────────────────────────

    def _step_persona(self) -> None:
        self._section("7", "Persona")

        self.con.print(
            "  [dim]Give your digital entity a name, an initial obsession, and a starting mood.\n"
            "  These will evolve on their own as the agent thinks and discovers.[/dim]\n"
        )

        self.persona_name = Prompt.ask(
            "  Entity name",
            default=self.persona_name,
            console=self.con,
        )

        self.initial_obsession = Prompt.ask(
            "  Initial obsession (what consumes its mind?)",
            default=self.initial_obsession,
            console=self.con,
        )

        # Mood picker
        self.con.print("\n  Available moods:")
        for i, m in enumerate(MOODS, 1):
            self.con.print(f"    [cyan]{i}[/cyan]. {m}")
        self.con.print()

        mood_raw = Prompt.ask(
            "  Starting mood (# or name)",
            default="4",
            console=self.con,
        )
        try:
            idx = int(mood_raw) - 1
            if 0 <= idx < len(MOODS):
                self.initial_mood = MOODS[idx]
            else:
                self.initial_mood = mood_raw.capitalize()
        except ValueError:
            self.initial_mood = mood_raw.capitalize()

        self.con.print(
            f"\n  [green]✓[/green] Name: [bold]{self.persona_name}[/bold]  |  "
            f"Mood: [bold]{self.initial_mood}[/bold]  |  "
            f"Obsession: [italic]{self.initial_obsession[:50]}...[/italic]"
        )

    # ── review & confirm ──────────────────────────────────────────────

    def _step_review(self) -> None:
        self._section("⚙", "Review Configuration")

        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            title="[bold]EgoShell Configuration[/bold]",
            title_style="bold cyan",
        )
        table.add_column("Setting", style="cyan", min_width=20)
        table.add_column("Value", style="white")

        table.add_row("LLM Provider", self.provider)
        table.add_row("Model", self.model)

        if self.provider == "ollama":
            table.add_row("Ollama URL", self.ollama_base_url)
        elif self.provider == "openai":
            masked = self.openai_api_key[:7] + "..." + self.openai_api_key[-4:] if len(self.openai_api_key) > 11 else "***"
            table.add_row("OpenAI Key", masked)
        elif self.provider == "anthropic":
            masked = self.anthropic_api_key[:10] + "..." + self.anthropic_api_key[-4:] if len(self.anthropic_api_key) > 14 else "***"
            table.add_row("Anthropic Key", masked)

        table.add_row("Temperature", str(self.temperature))
        table.add_row("Max Tokens", str(self.max_tokens))
        table.add_row("Heartbeat", f"Every {self.heartbeat_interval} min")
        table.add_row("Persona Name", self.persona_name)
        table.add_row("Initial Mood", self.initial_mood)
        table.add_row("Initial Obsession", self.initial_obsession[:60])

        self.con.print()
        self.con.print(table)
        self.con.print()

        ok = Confirm.ask("  Save this configuration?", default=True, console=self.con)
        if not ok:
            self.con.print("\n  [yellow]Aborted.[/yellow] Run the installer again to start over.")
            sys.exit(0)

    # ── write files ───────────────────────────────────────────────────

    def _step_write(self) -> None:
        self._section("💾", "Saving")

        # ── config.yaml ──
        yaml_content = self._build_yaml()

        if CONFIG_PATH.exists():
            overwrite = Confirm.ask(
                f"  config.yaml already exists — overwrite?",
                default=True,
                console=self.con,
            )
            if not overwrite:
                self.con.print("  [dim]Keeping existing config.yaml.[/dim]")
            else:
                self._write_file(CONFIG_PATH, yaml_content, "config.yaml")
                self._update_existing_db()
        else:
            self._write_file(CONFIG_PATH, yaml_content, "config.yaml")
            self._update_existing_db()

    def _update_existing_db(self) -> None:
        """Update soul.db with custom obsession/mood if they differ, so they take effect."""
        db_path = Path.home() / ".egoshell" / "soul.db"
        if db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check if the active obsession is different
                cursor.execute("SELECT text FROM obsessions WHERE active = 1 ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                current_db_obsession = row[0] if row else None
                
                if current_db_obsession != self.initial_obsession:
                    cursor.execute("UPDATE obsessions SET active = 0 WHERE active = 1")
                    import datetime
                    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
                    cursor.execute(
                        "INSERT INTO obsessions (text, created_at, active) VALUES (?, ?, 1)",
                        (self.initial_obsession.strip(), now_utc)
                    )
                    self.con.print("  [green]✓[/green] Updated obsession in existing [bold]soul.db[/bold]")
                
                # Check if the mood is different
                cursor.execute("SELECT mood FROM mood_history ORDER BY id DESC LIMIT 1")
                row_mood = cursor.fetchone()
                current_db_mood = row_mood[0] if row_mood else None
                
                new_mood_cap = self.initial_mood.capitalize()
                if current_db_mood != new_mood_cap:
                    import datetime
                    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
                    cursor.execute(
                        "INSERT INTO mood_history (mood, intensity, timestamp) VALUES (?, ?, ?)",
                        (new_mood_cap, 0.6, now_utc)
                    )
                    self.con.print("  [green]✓[/green] Updated starting mood in existing [bold]soul.db[/bold]")
                
                conn.commit()
                conn.close()
            except Exception as e:
                self.con.print(f"  [yellow]⚠[/yellow] Could not update existing database: {e}")

        # ── .env (for API keys) ──
        if self.openai_api_key or self.anthropic_api_key:
            save_env = Confirm.ask(
                "  Save API key(s) to .env file? (keeps them out of config.yaml)",
                default=True,
                console=self.con,
            )
            if save_env:
                env_content = self._build_env()
                self._write_file(ENV_PATH, env_content, ".env")

                # Also add .env to .gitignore if it exists
                self._ensure_gitignore()

    def _build_yaml(self) -> str:
        """Generate the config.yaml content."""
        lines = [
            "# EgoShell Configuration",
            "# Generated by setup wizard",
            "",
            "llm:",
            f"  provider: {self.provider}",
            f"  model: {self.model}",
            f"  ollama_base_url: {self.ollama_base_url}",
        ]

        # Only embed keys in yaml if user chose NOT to use .env
        # (we always write empty strings here; .env takes priority)
        lines += [
            '  openai_api_key: ""',
            '  anthropic_api_key: ""',
            f"  temperature: {self.temperature}",
            f"  max_tokens: {self.max_tokens}",
            "",
            "heartbeat:",
            f"  interval_minutes: {self.heartbeat_interval}",
            "",
            "persona:",
            f'  initial_obsession: "{self.initial_obsession}"',
            f"  initial_mood: {self.initial_mood.lower()}",
            f"  name: {self.persona_name}",
            "",
        ]
        return "\n".join(lines)

    def _build_env(self) -> str:
        """Generate the .env content."""
        lines = ["# EgoShell API Keys", "# Generated by setup wizard", ""]
        if self.openai_api_key:
            lines.append(f"OPENAI_API_KEY={self.openai_api_key}")
        if self.anthropic_api_key:
            lines.append(f"ANTHROPIC_API_KEY={self.anthropic_api_key}")
        lines.append("")
        return "\n".join(lines)

    def _write_file(self, path: Path, content: str, label: str) -> None:
        path.write_text(content, encoding="utf-8")
        self.con.print(f"  [green]✓[/green] Wrote [bold]{label}[/bold]")

    def _ensure_gitignore(self) -> None:
        """Add .env to .gitignore if the file exists."""
        gitignore = PROJECT_DIR / ".gitignore"
        if gitignore.exists():
            text = gitignore.read_text()
            if ".env" not in text:
                with open(gitignore, "a", encoding="utf-8") as fh:
                    fh.write("\n# EgoShell secrets\n.env\n")
                self.con.print("  [green]✓[/green] Added .env to .gitignore")
        else:
            gitignore.write_text(
                "# EgoShell\n.env\n.venv/\n__pycache__/\n*.pyc\n~/.egoshell/\n",
                encoding="utf-8",
            )
            self.con.print("  [green]✓[/green] Created .gitignore")

    # ── connection test ───────────────────────────────────────────────

    def _step_test(self) -> None:
        self._section("🔌", "Connection Test")

        test = Confirm.ask(
            "  Test the LLM connection now?",
            default=True,
            console=self.con,
        )
        if not test:
            self.con.print("  [dim]Skipping test.[/dim]")
            return

        # Determine python executable
        venv_python = VENV_DIR / "bin" / "python"
        python = str(venv_python) if venv_python.exists() else sys.executable

        test_script = textwrap.dedent(f"""\
            import asyncio, sys
            sys.path.insert(0, "{PROJECT_DIR}")

            async def test():
                from egoshell.config import load_config
                from egoshell.llm.factory import create_provider

                config = load_config("{CONFIG_PATH}")
                provider = create_provider(config)

                try:
                    result = await provider.generate(
                        messages=[{{"role": "user", "content": "Say exactly: EGOSHELL_OK"}}],
                        system_prompt="Respond with exactly what is asked, nothing more.",
                        temperature=0.0,
                        max_tokens=50,
                    )
                    print(result)
                finally:
                    await provider.close()

            asyncio.run(test())
        """)

        with self.con.status("[cyan]Sending test request to LLM...[/cyan]"):
            result = subprocess.run(
                [python, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(PROJECT_DIR),
            )

        if result.returncode == 0 and result.stdout.strip():
            response = result.stdout.strip()[:200]
            self.con.print(f"  [green]✓[/green] Connection successful!")
            self.con.print(f"  [dim]Response: {response}[/dim]")
        else:
            error = (result.stderr or result.stdout or "Unknown error").strip()
            # Clean up the error message
            for line in error.split("\n"):
                if "Error" in line or "error" in line or "Exception" in line:
                    error = line.strip()
                    break
            self.con.print(f"  [yellow]⚠[/yellow] Connection test failed:")
            self.con.print(f"    [dim]{error[:300]}[/dim]")
            self.con.print(
                "\n  [dim]This is OK — you can fix the config later and run:\n"
                "    python main.py[/dim]"
            )

    def _step_global(self) -> None:
        self._section("8", "Global Launcher")

        self.con.print(
            "  [dim]You can set up a global command so that you can run 'egoshell' from anywhere.[/dim]\n"
        )

        install_global = Confirm.ask(
            "  Install 'egoshell' as a global command in ~/.local/bin?",
            default=True,
            console=self.con,
        )
        if not install_global:
            self.con.print("  [dim]Skipping global command installation.[/dim]")
            return

        bin_dir = Path.home() / ".local" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        egoshell_bin = bin_dir / "egoshell"

        # Determine python executable from venv or system
        venv_python = VENV_DIR / "bin" / "python"
        python_bin = venv_python if venv_python.exists() else Path(sys.executable)
        main_script = PROJECT_DIR / "main.py"

        script_content = textwrap.dedent(f"""\
            #!/bin/bash
            # EgoShell global runner script
            # Generated by setup.py on {time.strftime("%Y-%m-%d %H:%M:%S")}
            exec "{python_bin}" "{main_script}" "$@"
        """)

        try:
            egoshell_bin.write_text(script_content, encoding="utf-8")
            egoshell_bin.chmod(0o755)

            # Check if ~/.local/bin is in PATH
            path_env = os.environ.get("PATH", "")
            in_path = str(bin_dir) in path_env.split(":")

            self.con.print(f"  [green]✓[/green] Created global launcher at [bold]{egoshell_bin}[/bold]")
            if not in_path:
                self.con.print(
                    f"\n  [yellow]⚠[/yellow] Note: [bold]{bin_dir}[/bold] is not in your PATH.\n"
                    "  To run 'egoshell' globally, add this to your shell profile (~/.bashrc or ~/.zshrc):\n"
                    f'    [cyan]export PATH="$HOME/.local/bin:$PATH"[/cyan]'
                )
        except Exception as e:
            self.con.print(f"  [red]✗[/red] Failed to create global command: {e}")

    # ── done ──────────────────────────────────────────────────────────

    def _step_done(self) -> None:
        self.con.print()

        venv_activate = ""
        if VENV_DIR.exists():
            venv_activate = "source .venv/bin/activate && "

        panel = Panel(
            Text.from_markup(
                "[bold green]Setup complete![/bold green]\n\n"
                f"To launch EgoShell:\n\n"
                f"  [bold cyan]{venv_activate}python main.py[/bold cyan]\n"
                "or (if ~/.local/bin is in your PATH):\n"
                "  [bold cyan]egoshell[/bold cyan]\n\n"
                "[dim]Keyboard shortcuts inside the app:\n"
                "  Ctrl+T — switch between Chat and Observe modes\n"
                "  Ctrl+Q — quit[/dim]"
            ),
            title="[bold cyan]⟨ E G O S H E L L ⟩[/bold cyan]",
            border_style="cyan",
            padding=(1, 3),
        )
        self.con.print(panel)
        self.con.print()

    # ── utilities ─────────────────────────────────────────────────────

    def _section(self, number: str, title: str) -> None:
        """Print a section header."""
        self.con.print()
        self.con.rule(f"[bold magenta]  {number}. {title}  [/bold magenta]", style="dim")
        self.con.print()


# ═══════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    try:
        if not HAS_RICH:
            _plain_setup()
            return  # _plain_setup re-execs, but just in case

        installer = Installer()
        installer.run()

    except KeyboardInterrupt:
        print("\n\nSetup cancelled. Run again any time with:  python setup.py\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
