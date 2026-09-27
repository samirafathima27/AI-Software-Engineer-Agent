from pathlib import Path


WORKSPACE_ROOT = Path("workspace").resolve()


def _resolve_allowed_root(allowed_root: str | Path | None) -> Path:
    return Path(allowed_root).resolve() if allowed_root else WORKSPACE_ROOT


def _safe_path(
    file_path: str,
    allowed_root: str | Path | None = None,
) -> tuple[bool, Path, str]:
    """Ensure the requested path stays inside the allowed root."""
    root = _resolve_allowed_root(allowed_root)

    try:
        path = Path(file_path).resolve()

        if path == root:
            return False, path, "Cannot operate directly on the allowed root."

        path.relative_to(root)
        return True, path, ""

    except ValueError:
        return (
            False,
            Path(file_path),
            f"Access denied. Path must be inside: {root}",
        )
    except Exception as exc:
        return False, Path(file_path), str(exc)


def read_file(
    file_path: str,
    allowed_root: str | Path | None = None,
) -> str:
    safe, path, error = _safe_path(file_path, allowed_root)

    if not safe:
        return f"Error: {error}"
    if not path.exists():
        return f"Error: File not found: {file_path}"
    if not path.is_file():
        return f"Error: Path is not a file: {file_path}"

    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return f"Error reading file: {exc}"


def list_files(
    directory: str,
    allowed_root: str | Path | None = None,
) -> str:
    safe, path, error = _safe_path(directory, allowed_root)

    if not safe:
        return f"Error: {error}"
    if not path.exists():
        return f"Error: Directory not found: {directory}"
    if not path.is_dir():
        return f"Error: Not a directory: {directory}"

    excluded = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
    }

    files = []
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        if any(part in excluded for part in item.parts):
            continue
        files.append(str(item))

    return "\n".join(files) if files else "No files found."


def write_file(
    file_path: str,
    content: str,
    allowed_root: str | Path | None = None,
) -> str:
    safe, path, error = _safe_path(file_path, allowed_root)

    if not safe:
        return f"Error: {error}"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Successfully wrote file: {file_path}"
    except Exception as exc:
        return f"Error writing file: {exc}"


def create_file(
    file_path: str,
    content: str,
    allowed_root: str | Path | None = None,
) -> str:
    safe, path, error = _safe_path(file_path, allowed_root)

    if not safe:
        return f"Error: {error}"
    if path.exists():
        return f"Error: File already exists: {file_path}"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Successfully created file: {file_path}"
    except Exception as exc:
        return f"Error creating file: {exc}"


def delete_file(
    file_path: str,
    allowed_root: str | Path | None = None,
) -> str:
    safe, path, error = _safe_path(file_path, allowed_root)

    if not safe:
        return f"Error: {error}"
    if not path.exists():
        return f"Error: File not found: {file_path}"
    if not path.is_file():
        return f"Error: Not a file: {file_path}"

    try:
        path.unlink()
        return f"Successfully deleted: {file_path}"
    except Exception as exc:
        return f"Error deleting file: {exc}"
