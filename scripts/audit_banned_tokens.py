"""Audit codebase for banned tokens and behavioral stubs."""

import sys
from pathlib import Path

BANNED_TOKENS = [
    "localhost",
    "127.0.0.1",
    "TODO",
    "FIXME",
    "NotImplementedException",
]

TARGET_DIRS = ["src", "projects"]


def audit_tokens() -> int:
    """Scan source files for banned tokens and patterns."""
    violations: list[tuple[str, int, str, str]] = []

    for target in TARGET_DIRS:
        target_path = Path(target)
        if not target_path.exists():
            continue

        for py_file in target_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as err:
                print(f"Warning: could not read {py_file}: {err}")
                continue

            lines = content.splitlines()
            for line_no, line in enumerate(lines, start=1):
                for token in BANNED_TOKENS:
                    if token in line:
                        violations.append((str(py_file), line_no, token, line.strip()))

    if violations:
        print(f"FAILED: Found {len(violations)} banned token violation(s):")
        for file_path, line_no, token, snippet in violations:
            print(f"  {file_path}:{line_no} contains banned token '{token}' -> {snippet}")
        return 1

    print("SUCCESS: 0 banned tokens found across audited directories.")
    return 0


if __name__ == "__main__":
    sys.exit(audit_tokens())
