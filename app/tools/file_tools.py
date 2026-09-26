from pathlib import Path


WORKSPACE_ROOT = Path("workspace").resolve()


def _safe_path(file_path: str) -> tuple[bool, Path, str]:
    """
    Ensure the requested path stays inside workspace/.
    """

    try:
        path = Path(file_path).resolve()

        if path == WORKSPACE_ROOT:
            return False, path, "Cannot operate directly on workspace root."

        if WORKSPACE_ROOT not in path.parents:
            return (
                False,
                path,
                f"Access denied. File must be inside: {WORKSPACE_ROOT}"
            )

        return True, path, ""

    except Exception as e:
        return False, Path(file_path), str(e)


def read_file(file_path: str) -> str:
    """Read a text file."""

    safe, path, error = _safe_path(file_path)

    if not safe:
        return f"Error: {error}"

    if not path.exists():
        return f"Error: File not found: {file_path}"

    if not path.is_file():
        return f"Error: Path is not a file: {file_path}"

    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

    except Exception as e:
        return f"Error reading file: {e}"


def list_files(directory: str) -> str:
    """List files inside a workspace directory."""

    safe, path, error = _safe_path(directory)

    if not safe:
        return f"Error: {error}"

    if not path.exists():
        return f"Error: Directory not found: {directory}"

    if not path.is_dir():
        return f"Error: Not a directory: {directory}"

    files = []

    for item in path.rglob("*"):

        if item.is_file():

            # Skip common unwanted directories
            if any(
                part in {
                    ".git",
                    ".venv",
                    "venv",
                    "__pycache__",
                    "node_modules"
                }
                for part in item.parts
            ):
                continue

            files.append(str(item))

    if not files:
        return "No files found."

    return "\n".join(files)


def write_file(
    file_path: str,
    content: str
) -> str:
    """
    Create a new file or completely replace
    an existing file.
    """

    safe, path, error = _safe_path(file_path)

    if not safe:
        return f"Error: {error}"

    try:

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        path.write_text(
            content,
            encoding="utf-8"
        )

        return (
            f"Successfully wrote file: "
            f"{file_path}"
        )

    except Exception as e:
        return f"Error writing file: {e}"


def create_file(
    file_path: str,
    content: str
) -> str:
    """
    Create a new file.

    Does not overwrite an existing file.
    """

    safe, path, error = _safe_path(file_path)

    if not safe:
        return f"Error: {error}"

    if path.exists():
        return (
            f"Error: File already exists: "
            f"{file_path}"
        )

    try:

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        path.write_text(
            content,
            encoding="utf-8"
        )

        return (
            f"Successfully created file: "
            f"{file_path}"
        )

    except Exception as e:
        return f"Error creating file: {e}"


def delete_file(file_path: str) -> str:
    """
    Delete a file inside workspace.

    Kept separate from the agent's default tools
    for now so accidental deletion is avoided.
    """

    safe, path, error = _safe_path(file_path)

    if not safe:
        return f"Error: {error}"

    if not path.exists():
        return f"Error: File not found: {file_path}"

    if not path.is_file():
        return f"Error: Not a file: {file_path}"

    try:

        path.unlink()

        return (
            f"Successfully deleted: "
            f"{file_path}"
        )

    except Exception as e:
        return f"Error deleting file: {e}"