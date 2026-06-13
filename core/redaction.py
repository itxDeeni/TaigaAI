import re

REDACT_PREFIX = "[REDACTED_"

PATTERNS = [
    ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS_SECRET_KEY", re.compile(r"(?i)(aws.?secret.?access.?key|aws.?secret.?key)\s*[=:]\s*['\"]?[0-9a-zA-Z/+]{40}")),
    ("GITHUB_TOKEN", re.compile(r"gh[pso]_[0-9a-zA-Z]{36}")),
    ("GITLAB_TOKEN", re.compile(r"glpat-[0-9a-zA-Z\-_]{20,}")),
    ("JWT_TOKEN", re.compile(r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+")),
    ("BEARER_TOKEN", re.compile(r"(?i)bearer\s+[a-zA-Z0-9._\-+/=]{20,}")),
    ("PEM_KEY", re.compile(r"-----BEGIN\s?(RSA|DSA|EC|OPENSSH|PRIVATE)\s?KEY-----")),
    ("DATABASE_URL", re.compile(r"(postgres|mysql|mongodb|redis)://[^@\s]+@")),
    ("SLACK_TOKEN", re.compile(r"xox[baprs]-[0-9a-zA-Z\-]{10,}")),
    ("SSH_KEY", re.compile(r"-----BEGIN\s?(RSA|DSA|EC|OPENSSH)\s?PRIVATE\s?KEY-----")),
    ("DISCORD_TOKEN", re.compile(r"[MN][A-Za-z\d]{23,25}\.[A-Za-z\d]{6,7}\.[A-Za-z\d_-]{27,}")),
    ("HEROKU_API_KEY", re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")),
    ("GOOGLE_API_KEY", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("GOOGLE_CLIENT_SECRET", re.compile(r"[0-9a-zA-Z_\-]{24}-[0-9a-zA-Z_\-]{24}")),
    ("FACEBOOK_SECRET", re.compile(r"[0-9a-f]{32}")),
    ("TWILIO_SECRET", re.compile(r"SK[0-9a-fA-F]{32}")),
    ("STRIPE_API_KEY", re.compile(r"(?:sk|pk)_(?:live|test)_[0-9a-zA-Z]{24,}")),
    ("PASSWORD_INLINE", re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"&;]{8,}")),
    ("API_KEY_INLINE", re.compile(r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"]?[0-9a-zA-Z_\-]{16,}")),
    ("SECRET_INLINE", re.compile(r"(?i)(secret)\s*[=:]\s*['\"]?[0-9a-zA-Z_\-]{16,}")),
]


def _length_preserving_mask(name, original):
    suffix = f"{name}_" + "_" * (len(original) - len(name) - len(REDACT_PREFIX) - 2)
    suffix = suffix[:max(0, len(original) - len(REDACT_PREFIX) - 1)]
    return f"{REDACT_PREFIX}{suffix}]"


def redact_text(text):
    for name, pattern in PATTERNS:
        def make_replacer(n=name):
            def replacer(match):
                return _length_preserving_mask(n, match.group(0))
            return replacer
        text = pattern.sub(make_replacer(), text)
    return text


def redact_text_verbose(text):
    results = []
    for name, pattern in PATTERNS:
        count_before = len(results)
        def make_replacer(n=name, r=results):
            def replacer(match):
                r.append((n, match.group(0)))
                return _length_preserving_mask(n, match.group(0))
            return replacer
        text = pattern.sub(make_replacer(), text)
    return text, results
