"""Safe path resolution utilities preventing directory traversal."""

from pathlib import Path


def validate_safe_path(base_dir: str | Path, target_path: str | Path) -> Path:
    """Resolve and validate that target_path resides strictly within base_dir.

    Raises:
        ValueError: If path traversal or escaping base_dir is detected.
        FileNotFoundError: If the target file does not exist.
    """
    base_resolved = Path(base_dir).resolve()
    target = Path(target_path)

    if target.is_absolute():
        resolved_target = target.resolve()
    else:
        resolved_target = (base_resolved / target).resolve()

    try:
        resolved_target.relative_to(base_resolved)
    except ValueError as err:
        raise ValueError(
            f"Path traversal detected: target '{target_path}' resolves to '{resolved_target}', "
            f"which is outside base directory '{base_resolved}'"
        ) from err

    if not resolved_target.exists():
        raise FileNotFoundError(f"File not found: {resolved_target}")

    return resolved_target
