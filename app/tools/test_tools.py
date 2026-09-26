from pathlib import Path
import subprocess
import sys


WORKSPACE_ROOT = Path("workspace").resolve()


def _validate_path(path: str) -> Path:

    target = Path(path).resolve()

    try:
        target.relative_to(WORKSPACE_ROOT)
    except ValueError:
        raise ValueError(
            f"Path outside workspace is not allowed: {path}"
        )

    return target


def run_python_file(file_path: str) -> str:

    path = _validate_path(file_path)

    if not path.exists():
        return f"Error: File not found: {file_path}"

    if path.suffix != ".py":
        return "Error: Only Python files can be executed."

    try:

        result = subprocess.run(
            [
                sys.executable,
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(path.parent),
        )

        return (
            f"Exit code: {result.returncode}\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )

    except subprocess.TimeoutExpired:
        return "Error: Python execution timed out."


def run_pytest(directory: str) -> str:

    path = _validate_path(directory)

    if not path.exists():
        return f"Error: Directory not found: {directory}"

    if not path.is_dir():
        return f"Error: Not a directory: {directory}"

    try:

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(path),
        )

        return (
            f"Exit code: {result.returncode}\n\n"
            f"PYTEST OUTPUT:\n"
            f"{result.stdout}\n"
            f"{result.stderr}"
        )

    except subprocess.TimeoutExpired:
        return "Error: pytest execution timed out."