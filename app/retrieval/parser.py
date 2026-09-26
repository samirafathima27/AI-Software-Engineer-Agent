import ast
from pathlib import Path


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
}


def parse_python_file(file_path: str) -> list[dict]:
    """
    Parse a single Python file using Python AST.

    Returns structured information about:
    - functions
    - classes
    - methods
    - imports
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if path.suffix != ".py":
        raise ValueError(
            "Only Python files are supported."
        )

    source_code = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source_code,
        filename=str(path),
    )

    results = []

    for node in ast.walk(tree):

        # -----------------------------
        # Functions
        # -----------------------------

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):

            results.append(
                {
                    "type": "function",
                    "name": node.name,
                    "file": str(path),
                    "line_start": node.lineno,
                    "line_end": getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                    "parameters": [
                        arg.arg
                        for arg in node.args.args
                    ],
                    "source": ast.get_source_segment(
                        source_code,
                        node,
                    ),
                }
            )

        # -----------------------------
        # Classes
        # -----------------------------

        elif isinstance(
            node,
            ast.ClassDef
        ):

            results.append(
                {
                    "type": "class",
                    "name": node.name,
                    "file": str(path),
                    "line_start": node.lineno,
                    "line_end": getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                    "methods": [
                        child.name
                        for child in node.body
                        if isinstance(
                            child,
                            (
                                ast.FunctionDef,
                                ast.AsyncFunctionDef,
                            ),
                        )
                    ],
                    "source": ast.get_source_segment(
                        source_code,
                        node,
                    ),
                }
            )

        # -----------------------------
        # Imports
        # -----------------------------

        elif isinstance(
            node,
            ast.Import
        ):

            for alias in node.names:

                results.append(
                    {
                        "type": "import",
                        "name": alias.name,
                        "file": str(path),
                        "line_start": node.lineno,
                        "line_end": getattr(
                            node,
                            "end_lineno",
                            node.lineno,
                        ),
                        "source": ast.get_source_segment(
                            source_code,
                            node,
                        ),
                    }
                )

        elif isinstance(
            node,
            ast.ImportFrom
        ):

            module = node.module or ""

            for alias in node.names:

                results.append(
                    {
                        "type": "import",
                        "name": (
                            f"{module}.{alias.name}"
                            if module
                            else alias.name
                        ),
                        "file": str(path),
                        "line_start": node.lineno,
                        "line_end": getattr(
                            node,
                            "end_lineno",
                            node.lineno,
                        ),
                        "source": ast.get_source_segment(
                            source_code,
                            node,
                        ),
                    }
                )

    return results


def scan_repository(
    repository_path: str = "workspace",
) -> list[dict]:
    """
    Scan the repository and parse every Python file.
    """

    root = Path(repository_path)

    if not root.exists():
        raise FileNotFoundError(
            f"Repository not found: {repository_path}"
        )

    results = []

    for path in root.rglob("*.py"):

        if any(
            directory in path.parts
            for directory in IGNORED_DIRECTORIES
        ):
            continue

        try:

            parsed = parse_python_file(
                str(path)
            )

            results.extend(parsed)

        except SyntaxError as e:

            results.append(
                {
                    "type": "syntax_error",
                    "file": str(path),
                    "error": str(e),
                }
            )

        except Exception as e:

            results.append(
                {
                    "type": "error",
                    "file": str(path),
                    "error": str(e),
                }
            )

    return results


def print_repository_structure(
    repository_path: str = "workspace",
):
    """
    Print a human-readable representation
    of the parsed repository.
    """

    results = scan_repository(
        repository_path
    )

    print(
        "\n========================================"
    )

    print(
        "      REPOSITORY CODE STRUCTURE"
    )

    print(
        "========================================"
    )

    for item in results:

        item_type = item.get(
            "type"
        )

        file_path = item.get(
            "file"
        )

        name = item.get(
            "name",
            "",
        )

        line_start = item.get(
            "line_start",
            "",
        )

        line_end = item.get(
            "line_end",
            "",
        )

        if item_type == "function":

            parameters = ", ".join(
                item.get(
                    "parameters",
                    [],
                )
            )

            print(
                f"\nFUNCTION: {name}"
            )

            print(
                f"  File: {file_path}"
            )

            print(
                f"  Lines: {line_start}-{line_end}"
            )

            print(
                f"  Parameters: {parameters}"
            )

        elif item_type == "class":

            methods = ", ".join(
                item.get(
                    "methods",
                    [],
                )
            )

            print(
                f"\nCLASS: {name}"
            )

            print(
                f"  File: {file_path}"
            )

            print(
                f"  Lines: {line_start}-{line_end}"
            )

            print(
                f"  Methods: {methods}"
            )

        elif item_type == "import":

            print(
                f"\nIMPORT: {name}"
            )

            print(
                f"  File: {file_path}"
            )

            print(
                f"  Line: {line_start}"
            )

        elif item_type == "syntax_error":

            print(
                f"\nSYNTAX ERROR: {file_path}"
            )

            print(
                f"  {item.get('error')}"
            )

        elif item_type == "error":

            print(
                f"\nERROR: {file_path}"
            )

            print(
                f"  {item.get('error')}"
            )


if __name__ == "__main__":

    print_repository_structure(
        "workspace"
    )