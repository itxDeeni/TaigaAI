# 🛡️ Security Policy & Architecture Audit

This document provides a detailed security posture analysis, architectural overview, threat assessment, and the implemented security controls for the **TaigaAI Workstation Engine**.

---

## 🗺️ System Data-Flow & Architecture

The workstation engine employs a zero-autonomy, read-only system structure. AI reasoning is strictly separated from local file write operations and shell execution.

```mermaid
graph TD
    User([User CLI Call]) --> |Positional Args| Security[core.security]
    User --> |Piped Stdin| Context[core.context_builder]
    
    subgraph Sandboxing & Validation
        Security -->|1. Validate CWD| CWDCheck{Inside Allowed Paths?}
        Security -->|2. Resolve & Verify File Paths| PathCheck{Under Whitelist & <5MB?}
        CWDCheck -- No --> Abort[Exit 1: Security Violation]
        PathCheck -- No --> Abort
    end
    
    CWDCheck -- Yes --> Context
    PathCheck -- Yes --> ReadFile[Read File Contents] --> Context
    
    Context -->|3. Escaped CDATA & XML Sanitization| Client[core.ollama_client]
    
    subgraph Core Execution Engine
        Client -->|4. Generate Cache Hash| Cache[core.cache]
        Cache -->|Cache Hit| FastOut[Output to Stdout <1ms]
        Cache -->|Cache Miss| Fallback{Query Ollama Model}
        
        Fallback -->|Primary Model Fails / Missing| PullCheck{Model Locally Found?}
        PullCheck -- No & Interactive -- PromptUser[User Choice to Pull] --> PullAPI[POST /api/pull Stream progress]
        PullAPI --> Validator[core.output_validator]
        PullCheck -- Yes --> Validator
        
        Validator -->|Validation Fails| Correct[Auto-Correct Prompt Loop]
        Correct -->|Success / Retry| Output[Write to Stdout & Bounded Cache Prune]
        Validator -->|Validation Passes| Output
    end
    
    Output --> Terminal([User Terminal Output])
    FastOut --> Terminal
```

---

## 🔍 Hardened Security Posture & Sandbox Controls

### 🛡️ Active Safeguards

1. **Canonical Path Resolution**: Uses Python's `Path(file_path).resolve()` to handle symbolic links, relative traversal operations (`../`), and redundant path segments before applying any boundaries.
2. **Path Whitelisting**: Resolves and verifies target files against whitelisted directories defined in `config.json` (with dynamic expansion of `~` home paths).
3. **No Direct Execution**: The engine acts solely as a read-only analyst. System command recommendations are output as text, ensuring a secure air-gap where execution requires explicit human intervention.
4. **Strict Format Enforcer**: The `OutputValidator` performs high-precision multi-block regular expression parsing to guarantee outputs comply with strict schema layouts and severities before returning to standard output.
5. **Memory DoS Boundaries**: Imposes an explicit **5MB size threshold** on all file read operations to prevent system lockup and memory exhaustion from massive files.
6. **Prompt Injection Isolation**: Automatically sanitizes nested XML and CDATA tag sequences inside source files and prepends a strong sandbox isolation header instructing the LLM to treat inputs strictly as untrusted text.
7. **Cache Footprint Bounding**: Automatically auto-prunes the local cache on every single new write operation, restricting the SQLite cache to the **200 most recent queries** via transaction `rowid` ordering to prevent disk storage bloat.
8. **Interactive Model Access Isolation**: Intercepts Ollama model-not-found (404) exceptions. If run in an interactive terminal (`isatty`), it explicitly prompts the developer for approval before performing streaming API pulls. Non-interactive tasks fail safe instead of running quiet background downloads.

---

## 🚀 Implemented Hardening Details

The following sections document the specific technical implementations added to mitigate security risks:

### 1. High-Precision Regex Format Validator
Upgraded from basic substring matching to sequential regular expression parsing in [core/output_validator.py](core/output_validator.py).

```python
import re

# Severity mapping and field order enforcement
severity_match = re.search(r"^\s*Severity:\s*(Low|Medium|High)\b", block, re.IGNORECASE | re.MULTILINE)
if not severity_match:
    return False, "Block invalid: Severity must be Low, Medium, or High"
```

### 2. Safety File Size Constraints
Added to [core/security.py](core/security.py) immediately after verifying path existence.

```python
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

if resolved_path.is_file() and resolved_path.stat().st_size > MAX_FILE_SIZE_BYTES:
    print("Security Violation: File exceeds safety limit of 5MB!", file=sys.stderr)
    sys.exit(1)
```

### 3. XML Context Escaping & Security Notice
Integrated in [core/context_builder.py](core/context_builder.py).

```python
def _sanitize(self, content):
    # Escape tags that could prematurely close context containers
    return content.replace("</context_source>", "<\\/context_source>").replace("]]>", "]]&gt;")
```
Plus, a runtime warning notice is injected directly above the content inputs during generation to prevent logical instruction hijacking.

### 4. Cache Bounding via RowID Eviction
Added inside [core/cache.py](core/cache.py) to bound the database footprint.

```python
# Auto-prune cache database to keep only the 200 most recent entries using rowid insertion order
conn.execute(
    """
    DELETE FROM prompt_cache WHERE rowid NOT IN (
        SELECT rowid FROM prompt_cache ORDER BY rowid DESC LIMIT 200
    )
    """
)
```

### 5. Prioritized Multi-Location Configuration Discovery
Added in [core/security.py](core/security.py) to support native user path lookups and config persistence across workspace updates.

1. **Workspace Path**: `Path(__file__).resolve().parent.parent / "config.json"` (Developer local overrides).
2. **User Config Folder**:
   - Linux/macOS: `~/.config/taiga-ai/config.json`
   - Windows: `%APPDATA%/taiga-ai/config.json`
