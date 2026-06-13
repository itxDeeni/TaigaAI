import json
import uuid
import sys
import time
from pathlib import Path
from datetime import datetime

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from core.cache import LocalAICache
from core.ollama_client import OllamaClient
from core.context_builder import ContextBuilder
from core.security import load_config, validate_cwd

COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_TEAL = "\033[38;5;38m"
COLOR_RED = "\033[38;5;196m"
COLOR_AMBER = "\033[38;5;214m"
COLOR_GREEN = "\033[38;5;82m"
COLOR_GRAY = "\033[38;5;244m"

MAX_RAW_TURNS = 4
TOKEN_BUDGET_PCT = 0.7

style = Style.from_dict({
    "prompt": "ansicyan bold",
    "command": "ansiyellow",
    "status": "default",
})


class ChatEngine:
    def __init__(self, model=None, system_prompt=None, session_name=None, ollama_url=None):
        self.config = load_config()
        models = self.config.get("models", {})
        self.model = model or models.get("coder", "qwen2.5-coder")
        self.ollama_url = ollama_url or self.config.get("ollama_url", "http://localhost:11434")
        self.system_prompt = system_prompt
        self.client = OllamaClient(base_url=self.ollama_url)
        self.cache = LocalAICache()

        self.session_id = str(uuid.uuid4())
        self.session_name = session_name or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.messages = []
        self.recent_raw_turns = []
        self.early_summary = ""

        self.project_dir = Path.cwd()
        self._load_project_config()

    def _load_project_config(self):
        project_cfg = self.project_dir / ".taiga" / "config.json"
        if project_cfg.exists():
            try:
                with open(project_cfg) as f:
                    proj = json.load(f)
                if "model" in proj:
                    self.model = proj["model"]
                if "system_prompt" in proj:
                    self.system_prompt = proj["system_prompt"]
            except Exception:
                pass

    def _estimate_tokens(self, text):
        return int(len(text) / 4.0) + 1

    def _save_session(self):
        try:
            conn = self.cache._conn()
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (id, name, messages, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (self.session_id, self.session_name, json.dumps(self.messages))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"{COLOR_GRAY}[cache] session save failed: {e}{COLOR_RESET}", file=sys.stderr)

    def _load_session(self, session_id):
        try:
            conn = self.cache._conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, messages FROM sessions WHERE id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                self.session_id = row[0]
                self.session_name = row[1]
                self.messages = json.loads(row[2])
                return True
        except Exception as e:
            print(f"{COLOR_GRAY}[cache] session load failed: {e}{COLOR_RESET}", file=sys.stderr)
        return False

    def _list_sessions(self):
        try:
            conn = self.cache._conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, updated_at FROM sessions ORDER BY updated_at DESC LIMIT 20"
            )
            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception:
            return []

    def _delete_session(self, session_id):
        try:
            conn = self.cache._conn()
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def _build_context(self, user_input):
        builder = ContextBuilder(
            token_budget=int(self._estimate_tokens(self.system_prompt or "") * TOKEN_BUDGET_PCT),
            system_prompt=self.system_prompt
        )
        builder.set_hybrid_buffer(
            system_prompt=self.system_prompt,
            recent_raw_turns=self.recent_raw_turns[-MAX_RAW_TURNS:],
            early_summary=self.early_summary
        )
        return builder.build(user_instruction=user_input)

    def _add_turn(self, role, content):
        turn = {"role": role, "content": content, "timestamp": time.time()}
        self.messages.append(turn)
        self.recent_raw_turns.append(f"{role}: {content}")

        if len(self.recent_raw_turns) > MAX_RAW_TURNS + 5:
            excess = self.recent_raw_turns[:-(MAX_RAW_TURNS + 1)]
            summary = "; ".join(excess)
            if self.early_summary:
                self.early_summary = f"{self.early_summary}; {summary}"
            else:
                self.early_summary = summary
            self.recent_raw_turns = self.recent_raw_turns[-(MAX_RAW_TURNS + 1):]

    def _handle_command(self, cmd_text):
        parts = cmd_text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("/exit", "/quit"):
            self._save_session()
            print(f"{COLOR_GREEN}Session saved. Goodbye.{COLOR_RESET}")
            sys.exit(0)

        elif cmd == "/clear":
            self.messages = []
            self.recent_raw_turns = []
            self.early_summary = ""
            print(f"{COLOR_GREEN}Session cleared.{COLOR_RESET}")
            return True

        elif cmd == "/save":
            name = arg or self.session_name
            self.session_name = name
            self._save_session()
            print(f"{COLOR_GREEN}Session saved as '{name}'.{COLOR_RESET}")
            return True

        elif cmd == "/load":
            if not arg:
                sessions = self._list_sessions()
                if not sessions:
                    print(f"{COLOR_AMBER}No saved sessions.{COLOR_RESET}")
                    return True
                print(f"{COLOR_GRAY}Saved sessions:{COLOR_RESET}")
                for sid, name, updated in sessions:
                    short_sid = sid[:8]
                    print(f"  {COLOR_TEAL}{short_sid}{COLOR_RESET}  {name}  ({updated})")
                print(f"{COLOR_GRAY}Use /load <session_id_prefix> to load one.{COLOR_RESET}")
                return True
            sessions = self._list_sessions()
            for sid, name, updated in sessions:
                if sid.startswith(arg):
                    if self._load_session(sid):
                        self.recent_raw_turns = []
                        self.early_summary = ""
                        for m in self.messages[-MAX_RAW_TURNS * 2:]:
                            self.recent_raw_turns.append(f"{m['role']}: {m['content']}")
                        print(f"{COLOR_GREEN}Loaded session '{name}' ({len(self.messages)} turns).{COLOR_RESET}")
                    else:
                        print(f"{COLOR_RED}Failed to load session.{COLOR_RESET}")
                    return True
            print(f"{COLOR_AMBER}No session matching '{arg}'.{COLOR_RESET}")
            return True

        elif cmd == "/sessions":
            sessions = self._list_sessions()
            if not sessions:
                print(f"{COLOR_AMBER}No saved sessions.{COLOR_RESET}")
                return True
            print(f"{COLOR_GRAY}Saved sessions:{COLOR_RESET}")
            for sid, name, updated in sessions:
                short_sid = sid[:8]
                print(f"  {COLOR_TEAL}{short_sid}{COLOR_RESET}  {name}  ({updated})")
            return True

        elif cmd == "/delete":
            if not arg:
                print(f"{COLOR_AMBER}Usage: /delete <session_id_prefix>{COLOR_RESET}")
                return True
            sessions = self._list_sessions()
            for sid, name, updated in sessions:
                if sid.startswith(arg):
                    self._delete_session(sid)
                    print(f"{COLOR_GREEN}Deleted session '{name}'.{COLOR_RESET}")
                    return True
            print(f"{COLOR_AMBER}No session matching '{arg}'.{COLOR_RESET}")
            return True

        elif cmd == "/model":
            if arg:
                self.model = arg.strip()
                print(f"{COLOR_GREEN}Model switched to '{self.model}'.{COLOR_RESET}")
            else:
                print(f"{COLOR_TEAL}Current model: {self.model}{COLOR_RESET}")
            return True

        elif cmd == "/help":
            self._print_help()
            return True

        elif cmd.startswith("/"):
            print(f"{COLOR_AMBER}Unknown command: {cmd}{COLOR_RESET}")
            return True

        return False

    def _print_help(self):
        commands = [
            ("/exit, /quit", "Save and exit"),
            ("/clear", "Clear current session"),
            ("/save [name]", "Save session"),
            ("/load [id]", "Load session (or list sessions)"),
            ("/sessions", "List saved sessions"),
            ("/delete [id]", "Delete a saved session"),
            ("/model [name]", "Show or switch model"),
            ("/help", "Show this help"),
        ]
        print(f"{COLOR_GRAY}Commands:{COLOR_RESET}")
        for cmd, desc in commands:
            print(f"  {COLOR_TEAL}{cmd:<20}{COLOR_RESET} {desc}")
        print(f"{COLOR_GRAY}Type your message to chat. Alt+Enter for multi-line input.{COLOR_RESET}")

    def _format_timestamp(self):
        return datetime.now().strftime("%H:%M:%S")

    def run(self):
        validate_cwd()

        history = FileHistory(str(self.project_dir / ".taiga" / ".chat_history"))

        completer = WordCompleter([
            "/exit", "/quit", "/clear", "/save", "/load", "/sessions",
            "/delete", "/model", "/help"
        ], ignore_case=True)

        bindings = KeyBindings()

        session = PromptSession(
            history=history,
            auto_suggest=AutoSuggestFromHistory(),
            completer=completer,
            key_bindings=bindings,
            style=style,
            enable_history_search=True,
            vi_mode=False,
        )

        print(f"{COLOR_TEAL}{COLOR_BOLD}╔══════════════════════════════════════╗{COLOR_RESET}")
        print(f"{COLOR_TEAL}{COLOR_BOLD}║     TaigaAI Chat (model: {self.model:{16}}) ║{COLOR_RESET}")
        print(f"{COLOR_TEAL}{COLOR_BOLD}╚══════════════════════════════════════╝{COLOR_RESET}")
        print(f"{COLOR_GRAY}Type /help for commands. Alt+Enter for multi-line.{COLOR_RESET}")
        print()

        self._save_session()

        while True:
            try:
                user_input = session.prompt("taiga> ", style=style)
            except (KeyboardInterrupt, EOFError):
                self._save_session()
                print(f"\n{COLOR_GREEN}Session saved. Goodbye.{COLOR_RESET}")
                break

            if not user_input.strip():
                continue

            if self._handle_command(user_input):
                self._save_session()
                continue

            context = self._build_context(user_input)
            self._add_turn("user", user_input)

            print(f"{COLOR_GRAY}[{self._format_timestamp()}]{COLOR_RESET}", end=" ", file=sys.stderr)
            success = self.client.query(
                model=self.model,
                prompt=context,
                system_prompt=self.system_prompt,
                timeout=300,
            )
            print()

            if success:
                self._add_turn("assistant", "(streamed output above)")
                self._save_session()
