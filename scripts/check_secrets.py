"""Fail without printing secret values if Git's staged tree contains credentials."""

import re
import subprocess
from pathlib import Path

PATTERN = re.compile(rb"(?:sk-or-v1-|sk-proj-|sk-ant-api03-)[A-Za-z0-9_-]{20,}")


def main() -> int:
    paths = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
    key_path = Path(".secrets/openrouter.key")
    local_key = key_path.read_bytes().strip() if key_path.is_file() else b""
    failures = []
    for raw in filter(None, paths):
        path = raw.decode()
        parts = Path(path).parts
        filename = Path(path).name
        forbidden = ".secrets" in parts or (
            (filename == ".env" or filename.startswith(".env.")) and filename != ".env.example"
        )
        content = subprocess.check_output(["git", "show", ":" + path])
        if forbidden or PATTERN.search(content) or (local_key and local_key in content):
            failures.append(path)
    if failures:
        print("Secret check failed for these paths (values suppressed):")
        for path in failures:
            print(path)
        return 1
    print("Staged tree secret check passed; no credential values printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
