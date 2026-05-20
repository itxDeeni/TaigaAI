#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
from pathlib import Path

# Premium terminal styling colors
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_TEAL = "\033[38;5;38m"
COLOR_GREEN = "\033[38;5;40m"
COLOR_AMBER = "\033[38;5;214m"
COLOR_RED = "\033[38;5;196m"
COLOR_GRAY = "\033[38;5;244m"

def print_header(title):
    print(f"\n{COLOR_TEAL}{COLOR_BOLD}=== {title} ==={COLOR_RESET}\n")

def get_config_path():
    """Resolves config.json path prioritizing workspace overrides then standard global paths."""
    workspace_config = Path(__file__).resolve().parent.parent / "config.json"
    if workspace_config.exists():
        return workspace_config
    if os.name == "nt":
        system_config_dir = Path(os.environ.get("APPDATA", "~")).expanduser() / "taiga-ai"
    else:
        system_config_dir = Path("~/.config/taiga-ai").expanduser()
    return system_config_dir / "config.json"

def fetch_local_models(base_url="http://localhost:11434"):
    """Fetches list of downloaded model tags from the local Ollama server."""
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            return models, True
    except Exception:
        return [], False

def attempt_start_ollama():
    """Tries to activate Ollama via systemctl if offline on Linux."""
    if os.name == "nt":
        return False
    try:
        # Check if systemctl is available
        subprocess.run(["systemctl", "--version"], capture_output=True, check=True)
    except Exception:
        return False

    print(f"{COLOR_AMBER}Local Ollama server is currently offline.{COLOR_RESET}")
    choice = input("Would you like to try starting the Ollama systemd service? (y/N): ").strip().lower()
    if choice != "y":
        return False

    print("Attempting to start Ollama service...")
    try:
        # Try user-level service first
        res = subprocess.run(["systemctl", "--user", "start", "ollama"], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"{COLOR_GREEN}✔ Started Ollama user service successfully.{COLOR_RESET}")
            return True
        # Try system-level service
        res = subprocess.run(["sudo", "systemctl", "start", "ollama"], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"{COLOR_GREEN}✔ Started Ollama system service successfully.{COLOR_RESET}")
            return True
    except Exception as e:
        print(f"{COLOR_RED}Could not start Ollama service automatically: {e}{COLOR_RESET}")
    return False

def select_model(role, available_models, default_recommendation):
    """Interactively prompts user to select or input a model mapping."""
    print(f"{COLOR_BOLD}Configure model for Coder/Thinker/Security role: {COLOR_TEAL}{role.upper()}{COLOR_RESET}")
    
    # Analyze and rank models
    options = []
    recommended_idx = -1

    # 1. Add recommendations first if available locally
    for m in available_models:
        is_rec = False
        if role == "coder" and ("coder" in m or "qwen" in m or "deepseek" in m):
            is_rec = True
        elif role in ("thinker", "security") and ("llama" in m or "mistral" in m or "phi" in m):
            is_rec = True
            
        label = m
        if is_rec:
            label += f" {COLOR_GREEN}(Recommended - Found locally!){COLOR_RESET}"
            options.insert(0, (m, label, True))
        else:
            options.append((m, label, False))

    # Re-align recommended index
    for i, opt in enumerate(options):
        if opt[2]:
            recommended_idx = i
            break

    # If no local model is recommended, add default recommendation as first choice to download
    if recommended_idx == -1:
        options.insert(0, (default_recommendation, f"{default_recommendation} {COLOR_AMBER}(Recommended default - Will prompt download if missing){COLOR_RESET}", True))
        recommended_idx = 0

    # Add option for custom entry
    custom_idx = len(options) + 1
    
    # Display Options
    for idx, opt in enumerate(options, 1):
        marker = "➔ " if idx - 1 == recommended_idx else "  "
        print(f"{marker}{idx}) {opt[1]}")
    print(f"  {custom_idx}) Enter custom model tag...")

    # Get Input
    try:
        raw_val = input(f"\nSelect option [1-{custom_idx}] (Default option {recommended_idx + 1}): ").strip()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{COLOR_RED}Cancelled. Using default recommendation.{COLOR_RESET}")
        raw_val = ""

    if not raw_val:
        return options[recommended_idx][0]
    
    try:
        selection = int(raw_val)
        if 1 <= selection <= len(options):
            return options[selection - 1][0]
        elif selection == custom_idx:
            custom_model = input("Enter custom Ollama model tag (e.g. deepseek-coder:6.7b): ").strip()
            return custom_model if custom_model else default_recommendation
    except ValueError:
        pass
        
    print(f"{COLOR_AMBER}Invalid choice. Defaulting to recommendation: {options[recommended_idx][0]}{COLOR_RESET}")
    return options[recommended_idx][0]

def verify_pipeline_health(model, base_url="http://localhost:11434"):
    """Performs a 1-token trial check to confirm pipeline health."""
    print(f"\nRunning trial connection test using '{model}'...")
    try:
        url = f"{base_url}/api/generate"
        data = {
            "model": model,
            "prompt": "Hi",
            "stream": False,
            "options": {"num_predict": 1}
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print(f"{COLOR_GREEN}{COLOR_BOLD}✔ End-to-end local AI pipeline is 100% active and healthy!{COLOR_RESET}")
                return True
    except Exception as e:
        print(f"{COLOR_AMBER}Trial query warning: Server connected but model trial missed. {e}{COLOR_RESET}")
        print(f"{COLOR_GRAY}Note: Setup completed successfully, but you may need to download '{model}' via 'ollama pull {model}' before running.{COLOR_RESET}")
    return False

def main():
    print_header("TaigaAI Setup & Configuration Assistant")

    config_path = get_config_path()
    
    # Load existing or create new defaults
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception:
            config = {}
    else:
        config = {}

    config["allowed_paths"] = config.get("allowed_paths", [])
    config["models"] = config.get("models", {})
    config["ollama_url"] = config.get("ollama_url", "http://localhost:11434")

    # 1. Workspace Auto-Whitelisting discovery
    print_header("Workspace Whitelist Auto-Discovery")
    workspace_dir = Path(__file__).resolve().parent.parent
    whitelisted_current = False
    
    for p in config["allowed_paths"]:
        try:
            resolved_p = Path(p).expanduser().resolve()
            if workspace_dir == resolved_p or resolved_p in workspace_dir.parents:
                whitelisted_current = True
                break
        except Exception:
            continue

    if not whitelisted_current:
        # Prompt to whitelist current workspace
        target_whitelist = str(workspace_dir.parent if workspace_dir.name in ("safe-local-ai", "Taiga-ai") else workspace_dir)
        print(f"I detected you are installing from: {COLOR_TEAL}{workspace_dir}{COLOR_RESET}")
        print(f"To satisfy sandboxing checks, I recommend whitelisting: {COLOR_TEAL}{target_whitelist}{COLOR_RESET}")
        
        try:
            choice = input(f"Would you like to whitelist this directory now? (Y/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            choice = "y"
            
        if choice != "n":
            config["allowed_paths"].append(target_whitelist)
            # Clean and deduplicate allowed paths
            unique_paths = []
            for path in config["allowed_paths"]:
                if path not in unique_paths:
                    unique_paths.append(path)
            config["allowed_paths"] = unique_paths
            print(f"{COLOR_GREEN}✔ Added '{target_whitelist}' to whitelisted allowed paths.{COLOR_RESET}")
    else:
        print(f"{COLOR_GREEN}✔ Current workspace directory is already whitelisted and secure.{COLOR_RESET}")

    # 2. Ollama Connection Auto-Discovery
    print_header("Ollama Connection Diagnostics")
    models_list, online = fetch_local_models(config["ollama_url"])
    
    if not online:
        # Try to start the service automatically
        if attempt_start_ollama():
            # Wait briefly and retry query
            import time
            time.sleep(1.5)
            models_list, online = fetch_local_models(config["ollama_url"])

    if online:
        print(f"{COLOR_GREEN}✔ Connected successfully to Ollama server!{COLOR_RESET}")
        if models_list:
            print(f"Found {len(models_list)} local models downloaded: {', '.join(models_list)}")
        else:
            print(f"{COLOR_AMBER}No local models found. You may need to download models first.{COLOR_RESET}")
    else:
        print(f"{COLOR_AMBER}⚠️ Ollama server is offline or not responding. We will configure default recommended mappings.{COLOR_RESET}")

    # 3. Model Mapping Wizard
    print_header("Interactive Model Mapping Wizard")
    
    coder_model = select_model("coder", models_list, "qwen2.5-coder:3b")
    print()
    thinker_model = select_model("thinker", models_list, "llama3.2:3b")
    print()
    security_model = select_model("security", models_list, "llama3.2:3b")

    config["models"]["coder"] = coder_model
    config["models"]["thinker"] = thinker_model
    config["models"]["security"] = security_model

    # Save Configurations
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\n{COLOR_GREEN}{COLOR_BOLD}✔ Configuration successfully saved to: {config_path}{COLOR_RESET}")
    except Exception as e:
        print(f"\n{COLOR_RED}Error saving configurations to '{config_path}': {e}{COLOR_RESET}")
        sys.exit(1)

    # 4. Pipeline Diagnostic Checks
    if online:
        print_header("Local AI Pipeline Diagnostics")
        verify_pipeline_health(coder_model, config["ollama_url"])
    
    print(f"\n{COLOR_GREEN}{COLOR_BOLD}Setup assistant completed setup successfully!{COLOR_RESET}\n")

if __name__ == "__main__":
    main()
