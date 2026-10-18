"""Minimize credential-shaped text at untrusted input and model-output boundaries."""

import re

_CREDENTIALS = re.compile(
    r"(?:sk-or-v1-|sk-proj-|sk-ant-api03-)[A-Za-z0-9_-]+"
    r"|(?i:Bearer)\s+[A-Za-z0-9._~+/-]{8,}=*"
    r"|(?i:api[_-]?key|password|access[_-]?token|secret)\s*[=:]\s*[^\s\"'<>;,]+"
    r"|(?i:postgres(?:ql)?://)[^\s/@]+:[^\s/@]+@"
)


def redact_text(value: str, secrets: tuple[str, ...] = ()) -> str:
    for secret in secrets:
        if secret:
            value = value.replace(secret, "[REDACTED]")
    return _CREDENTIALS.sub("[REDACTED]", value)


def require_credential_free(value: str) -> None:
    if redact_text(value) != value:
        raise ValueError("Captured evidence must not contain credential-shaped text.")
