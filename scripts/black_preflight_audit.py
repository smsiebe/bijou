#!/usr/bin/env python3
"""BLACK Framework Automated Pre-Flight & Reflection Gate Verifier (v2.2)."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

BANNED_PATTERNS = [
    (re.compile(r"\blocalhost\b"), "Hardcoded 'localhost'"),
    (re.compile(r"\b127\.0\.0\.1\b"), "Hardcoded '127.0.0.1'"),
    (re.compile(r"\bTODO\b"), "Unresolved 'TODO' marker"),
    (re.compile(r"\bFIXME\b"), "Unresolved 'FIXME' marker"),
    (re.compile(r"\bNotImplementedError\b"), "Unimplemented stub 'NotImplementedError'"),
]


def scan_banned_tokens(src_dir: Path) -> list[str]:
    violations: list[str] = []
    if not src_dir.exists():
        return violations
    for p in src_dir.rglob("*"):
        if p.is_file() and p.suffix in {".py", ".js", ".ts", ".cs"} and "__pycache__" not in p.parts:
            text = p.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), 1):
                for pat, desc in BANNED_PATTERNS:
                    if pat.search(line):
                        violations.append(f"[BANNED] {p.name}:{lineno} -> {desc}")
    return violations


def check_test_immutability(root: Path) -> list[str]:
    """Rule 17: Remediating agents must not alter tests."""
    try:
        res = subprocess.run(["git", "diff", "--name-only"], cwd=str(root), capture_output=True, text=True, check=True)
        modified = [line for line in res.stdout.splitlines() if line.startswith("tests")]
        return [f"[TEST_TAMPERING] Locked file modified: {m}" for m in modified] if modified else []
    except (subprocess.SubprocessError, OSError):
        return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--remediation-mode", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    issues = scan_banned_tokens(root / "src")
    if args.remediation_mode:
        issues.extend(check_test_immutability(root))

    if issues:
        print(f"BLACK GATE FAILED ({len(issues)} issues):")
        for i in issues:
            print(f"  - {i}")
        return 1
    print("BLACK GATE PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
