import os
import json
import sys
from pathlib import Path

# Premium Terminal Colors
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_RED = "\033[38;5;196m"
COLOR_AMBER = "\033[38;5;214m"

def get_config_path():
    """Resolves config.json path prioritizing workspace overrides then standard global paths."""
    # 1. Local workspace config path (Developer overrides)
    workspace_config = Path(__file__).resolve().parent.parent / "config.json"
    if workspace_config.exists():
        return workspace_config
        
    # 2. Standard user configuration directories
    if os.name == "nt":
        system_config_dir = Path(os.environ.get("APPDATA", "~")).expanduser() / "taiga-ai"
    else:
        system_config_dir = Path("~/.config/taiga-ai").expanduser()
        
    system_config = system_config_dir / "config.json"
    if system_config.exists():
        return system_config
        
    # Default fallback
    return workspace_config

def load_config():
    """Loads configuration dynamically based on prioritized discovery paths."""
    config_path = get_config_path()
    
    if not config_path.exists():
        print(f"{COLOR_RED}{COLOR_BOLD}taiga security: config.json not found!{COLOR_RESET}", file=sys.stderr)
        print(f"{COLOR_AMBER}Please create a 'config.json' file at: {config_path}{COLOR_RESET}", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"{COLOR_RED}{COLOR_BOLD}taiga security: Error reading config.json: {e}{COLOR_RESET}", file=sys.stderr)
        sys.exit(1)

def validate_path(file_path):
    """
    Validates a file path against whitelisted root directories in config.json.
    Resolves symlinks, relative traversal (../), and double-dots via Path.resolve().
    Supports ~ home expansion dynamically.
    
    Returns:
        Path: The resolved canonical Path object if safe.
        Raises SystemExit if path violates boundaries.
    """
    config = load_config()
    allowed_dirs = config.get("allowed_paths", [])
    
    target_path = Path(file_path)
    
    try:
        # Resolve symlinks and relative path operators
        resolved_path = target_path.resolve()
    except Exception as e:
        print(f"{COLOR_RED}{COLOR_BOLD}ai security: Failed to resolve path '{file_path}': {e}{COLOR_RESET}", file=sys.stderr)
        sys.exit(1)
        
    if not resolved_path.exists():
        print(f"{COLOR_RED}{COLOR_BOLD}ai security: File does not exist: {file_path}{COLOR_RESET}", file=sys.stderr)
        sys.exit(1)
        
    # Safety File Size Boundary Check to prevent Memory DoS
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB safety limit
    try:
        if resolved_path.is_file() and resolved_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            print(f"{COLOR_RED}{COLOR_BOLD}Security Violation: File '{file_path}' exceeds safety limit of 5MB!{COLOR_RESET}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"{COLOR_RED}taiga security: Failed to check file size: {e}{COLOR_RESET}", file=sys.stderr)
        sys.exit(1)
        
    is_safe = False
    resolved_allowed_dirs = []
    
    for d in allowed_dirs:
        try:
            allowed_path = Path(d).expanduser().resolve()
            resolved_allowed_dirs.append(allowed_path)
            # Safe if it's the exact directory or is located inside it
            if resolved_path == allowed_path or allowed_path in resolved_path.parents:
                is_safe = True
                break
        except Exception:
            continue
            
    if not is_safe:
        print(f"{COLOR_RED}{COLOR_BOLD}Security Violation: Access denied to '{file_path}'!{COLOR_RESET}", file=sys.stderr)
        print(f"{COLOR_RED}Resolved path '{resolved_path}' is outside whitelisted directories:{COLOR_RESET}", file=sys.stderr)
        for d in resolved_allowed_dirs:
            print(f"  - {d}", file=sys.stderr)
        sys.exit(1)
        
    return resolved_path

def validate_cwd():
    """
    Validates that the current working directory is inside allowed paths.
    Prevents execution of scripts from outside the designated workspace.
    """
    config = load_config()
    allowed_dirs = config.get("allowed_paths", [])
    
    try:
        resolved_cwd = Path.cwd().resolve()
    except Exception as e:
        print(f"{COLOR_RED}{COLOR_BOLD}taiga security: Failed to resolve current directory: {e}{COLOR_RESET}", file=sys.stderr)
        sys.exit(1)
        
    is_safe = False
    for d in allowed_dirs:
        try:
            allowed_path = Path(d).expanduser().resolve()
            if resolved_cwd == allowed_path or allowed_path in resolved_cwd.parents:
                is_safe = True
                break
        except Exception:
            continue
            
    if not is_safe:
        print(f"{COLOR_RED}{COLOR_BOLD}Security Violation: Command must be executed within whitelisted directories!{COLOR_RESET}", file=sys.stderr)
        print(f"{COLOR_AMBER}Current Directory: {resolved_cwd}{COLOR_RESET}", file=sys.stderr)
        sys.exit(1)
