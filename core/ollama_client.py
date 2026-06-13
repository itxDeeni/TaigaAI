import json
import sys
import urllib.request
import urllib.error
import time
from pathlib import Path

# Add project root directory to path for robust core module resolution
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.cache import LocalAICache
from core.output_validator import OutputValidator
from core.redaction import redact_text

# Premium Terminal Colors
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_TEAL = "\033[38;5;38m"
COLOR_RED = "\033[38;5;196m"
COLOR_AMBER = "\033[38;5;214m"
COLOR_GRAY = "\033[38;5;244m"

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", default_timeout=300):
        self.base_url = base_url.rstrip("/")
        self.default_timeout = default_timeout
        self.cache = LocalAICache()

    def _get_local_tags(self):
        """Fetches list of downloaded model tags from the local Ollama server."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def query(self, model, prompt, system_prompt=None, max_tokens=None, timeout=None, tool_name=None):
        """
        Main query router with integrated Caching, Fallback chains, and Output validation.
        """
        timeout = timeout or self.default_timeout

        # 0. Phase 0.1: Secret redaction at pipeline entry (before cache, before Ollama)
        prompt = redact_text(prompt)
        if system_prompt:
            system_prompt = redact_text(system_prompt)

        # 1. Cache lookup for instant repeat execution
        cached_response = self.cache.get(model, f"{system_prompt or ''}\n{prompt}")
        if cached_response:
            print(f"{COLOR_GRAY}{COLOR_BOLD}[Taiga Cache Hit - Instant Response]{COLOR_RESET}", file=sys.stderr)
            sys.stdout.write(cached_response)
            sys.stdout.flush()
            print()
            return True

        # 2. Query execution with dynamic fallback model options
        local_tags = self._get_local_tags()
        
        # Find matches among installed tags to avoid pulling specific versions
        def find_local_match(pattern):
            for tag in local_tags:
                if pattern in tag:
                    return tag
            return None

        # Build dynamic, model-agnostic fallback chain
        model_chain = [model]
        
        # 1. Prioritize other active model mappings from user configuration
        try:
            from core.security import load_config
            config = load_config()
            for role_model in config.get("models", {}).values():
                if role_model and role_model not in model_chain:
                    model_chain.append(role_model)
        except Exception:
            pass

        # 2. Append other locally installed models to avoid pulling missing models
        for tag in local_tags:
            if tag not in model_chain:
                model_chain.append(tag)

        response_content = None
        used_model = None
        # Only stream in real-time if no strict validation contract is active
        should_stream = (tool_name is None)

        for target_model in model_chain:
            try:
                response_content = self._execute_http_call(
                    target_model, prompt, system_prompt, max_tokens, timeout, stream=should_stream
                )
                if response_content:
                    used_model = target_model
                    break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # Model is missing from local Ollama tags library
                    if sys.stdin.isatty():
                        print(f"\n{COLOR_AMBER}[Ollama] Model '{target_model}' not found locally.{COLOR_RESET}", file=sys.stderr)
                        try:
                            choice = input(f"Would you like to pull/download '{target_model}' now? (y/N): ").strip().lower()
                        except (KeyboardInterrupt, EOFError):
                            print(f"\n{COLOR_RED}Pull cancelled by user.{COLOR_RESET}", file=sys.stderr)
                            choice = 'n'
                        if choice == 'y':
                            if self.pull_model(target_model):
                                try:
                                    response_content = self._execute_http_call(
                                        target_model, prompt, system_prompt, max_tokens, timeout, stream=should_stream
                                    )
                                    if response_content:
                                        used_model = target_model
                                        break
                                except Exception as re_err:
                                    print(f"{COLOR_RED}Failed to query model after pull: {re_err}{COLOR_RESET}", file=sys.stderr)
                    else:
                        print(f"{COLOR_AMBER}Warning: Model '{target_model}' not found (404). Run 'ollama pull {target_model}' to download it.{COLOR_RESET}", file=sys.stderr)
                else:
                    print(f"{COLOR_AMBER}Warning: Model query '{target_model}' failed (HTTP {e.code}): {e.reason}. Attempting fallback...{COLOR_RESET}", file=sys.stderr)
            except Exception as e:
                # Try next model in fallback chain
                print(f"{COLOR_AMBER}Warning: Model '{target_model}' failed or connection issue: {e}. Attempting fallback...{COLOR_RESET}", file=sys.stderr)
                continue

        if not response_content:
            print(f"\n{COLOR_RED}{COLOR_BOLD}taiga client error: Failed to connect to local Ollama server.{COLOR_RESET}", file=sys.stderr)
            print(f"{COLOR_AMBER}Verify that the Ollama service is active. Run:{COLOR_RESET}", file=sys.stderr)
            print(f"  systemctl --user status ollama   (or systemctl status ollama)", file=sys.stderr)
            return False

        # 3. Output validation & automatic self-correcting format re-prompting
        if tool_name:
            is_valid, err_msg = OutputValidator.validate(tool_name, response_content)
            if not is_valid:
                print(f"{COLOR_AMBER}Format deviation detected. Invoking automatic self-correcting alignment loop...{COLOR_RESET}", file=sys.stderr)
                correction_prompt = f"""
Your previous output violated the strict structured contract:
{err_msg}

Please re-generate your analysis and conform strictly to the required layout. 
Do not include conversational preamble or markdown code blocks. 
Output ONLY the clean, structured format.

Previous analysis was:
{response_content}
"""
                try:
                    corrected_content = self._execute_http_call(
                        used_model, correction_prompt, system_prompt, max_tokens, timeout, stream=False
                    )
                    if corrected_content:
                        # Recheck corrected output
                        rev_valid, _ = OutputValidator.validate(tool_name, corrected_content)
                        if rev_valid:
                            response_content = corrected_content
                except Exception:
                    pass  # Fallback to returning original output if retry crashes

            # Now that validation and self-correction are complete, write final result to stdout
            sys.stdout.write(response_content)
            sys.stdout.flush()
            print()

        # 4. Save successful run to Local Cache
        self.cache.set(used_model, f"{system_prompt or ''}\n{prompt}", response_content)
        
        return True

    def _execute_http_call(self, model, prompt, system_prompt, max_tokens, timeout, stream=True):
        """Low-level Ollama API client execution."""
        url = f"{self.base_url}/api/generate"
        options = {}
        if max_tokens:
            options["num_predict"] = max_tokens

        data = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": options
        }
        if system_prompt:
            data["system"] = system_prompt

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        full_text = []
        with urllib.request.urlopen(req, timeout=timeout) as response:
            for line in response:
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    text = chunk.get("response", "")
                    full_text.append(text)
                    if stream:
                        sys.stdout.write(text)
                        sys.stdout.flush()
            if stream:
                print()
                
        return "".join(full_text)

    def pull_model(self, model):
        """Pulls a model from the Ollama library, streaming progress updates directly to stderr."""
        url = f"{self.base_url}/api/pull"
        data = {
            "name": model,
            "stream": True
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        print(f"{COLOR_TEAL}{COLOR_BOLD}[Ollama] Pulling model '{model}'...{COLOR_RESET}", file=sys.stderr)
        
        try:
            with urllib.request.urlopen(req, timeout=600) as response:  # 10 minutes timeout for model download
                last_status = ""
                for line in response:
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        status = chunk.get("status", "")
                        
                        # Extract progress details
                        total = chunk.get("total", 0)
                        completed = chunk.get("completed", 0)
                        
                        if total > 0:
                            percent = int((completed / total) * 100)
                            # Render a simple console progress bar
                            bar_length = 20
                            filled_length = int(bar_length * completed // total)
                            bar = "█" * filled_length + "-" * (bar_length - filled_length)
                            
                            # Standardize size representation (MB)
                            completed_mb = completed / (1024 * 1024)
                            total_mb = total / (1024 * 1024)
                            
                            progress_str = f"\r{COLOR_GRAY}{status}{COLOR_RESET} |{COLOR_TEAL}{bar}{COLOR_RESET}| {percent}% ({completed_mb:.1f}/{total_mb:.1f} MB)"
                            sys.stderr.write(progress_str)
                            sys.stderr.flush()
                        elif status != last_status:
                            sys.stderr.write(f"\r{COLOR_GRAY}{status}...{' ' * 20}{COLOR_RESET}\n")
                            sys.stderr.flush()
                            last_status = status
                print(f"\n{COLOR_TEAL}{COLOR_BOLD}✔ Model '{model}' successfully pulled and ready!{COLOR_RESET}\n", file=sys.stderr)
                return True
        except Exception as e:
            print(f"\n{COLOR_RED}Error: Failed to pull model '{model}': {e}{COLOR_RESET}", file=sys.stderr)
            return False
