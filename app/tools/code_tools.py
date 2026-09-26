from pathlib import Path
import difflib


WORKSPACE_ROOT = Path("workspace").resolve()


def _safe_path(file_path: str) -> tuple[bool, Path, str]:

    try:

        path = Path(file_path).resolve()

        if WORKSPACE_ROOT not in path.parents:
            return (
                False,
                path,
                f"Access denied. File must be inside: {WORKSPACE_ROOT}"
            )

        return True, path, ""

    except Exception as e:

        return (
            False,
            Path(file_path),
            str(e)
        )


def patch_file(
    file_path: str,
    old_text: str,
    new_text: str
) -> str:
    """
    Replace a specific piece of code inside a file.

    The replacement only happens if old_text
    exists exactly once.
    """

    safe, path, error = _safe_path(file_path)

    if not safe:
        return f"Error: {error}"

    if not path.exists():
        return f"Error: File not found: {file_path}"

    if not path.is_file():
        return f"Error: Not a file: {file_path}"

    try:

        content = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        occurrences = content.count(old_text)

        if occurrences == 0:
            return (
                "Error: The old code was not found "
                "in the file."
            )

        if occurrences > 1:
            return (
                "Error: The old code appears "
                f"{occurrences} times. "
                "Patch was not applied because "
                "the target is ambiguous."
            )

        updated_content = content.replace(
            old_text,
            new_text,
            1
        )

        path.write_text(
            updated_content,
            encoding="utf-8"
        )

        return (
            f"Successfully patched "
            f"{file_path}"
        )

    except Exception as e:

        return f"Error patching file: {e}"


def show_diff(
    file_path: str,
    old_content: str,
    new_content: str
) -> str:
    """
    Generate a unified diff between
    two versions of a file.
    """

    diff = difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        fromfile=f"{file_path} (old)",
        tofile=f"{file_path} (new)",
        lineterm=""
    )

    result = "\n".join(diff)

    if not result:
        return "No changes detected."

    return result