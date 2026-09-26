from pathlib import Path

from app.retrieval.parser import parse_python_file


def create_code_chunks(file_path: str) -> list[dict]:
    """
    Convert a Python file into searchable code chunks.

    Each function and class becomes a separate chunk.
    """

    path = Path(file_path)

    parsed_items = parse_python_file(
        str(path)
    )

    chunks = []

    for item in parsed_items:

        item_type = item.get("type")

        # We only want actual code structures
        # for semantic code search.
        if item_type not in {
            "function",
            "class",
        }:
            continue

        source = item.get(
            "source",
            ""
        )

        if not source:
            continue

        chunk = {
            "id": (
                f"{path}:"
                f"{item.get('line_start')}:"
                f"{item.get('name')}"
            ),

            "type": item_type,

            "name": item.get(
                "name",
                ""
            ),

            "file": str(path),

            "line_start": item.get(
                "line_start"
            ),

            "line_end": item.get(
                "line_end"
            ),

            "content": source,

            "text": (
                f"Type: {item_type}\n"
                f"Name: {item.get('name', '')}\n"
                f"File: {path}\n"
                f"Lines: "
                f"{item.get('line_start')}-"
                f"{item.get('line_end')}\n\n"
                f"{source}"
            ),
        }

        chunks.append(chunk)

    return chunks


def chunk_repository(
    repository_path: str = "workspace",
) -> list[dict]:
    """
    Scan the repository and create searchable
    code chunks for every Python file.
    """

    root = Path(
        repository_path
    )

    if not root.exists():
        raise FileNotFoundError(
            f"Repository not found: "
            f"{repository_path}"
        )

    ignored_directories = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
    }

    all_chunks = []

    for file_path in root.rglob("*.py"):

        if any(
            directory in file_path.parts
            for directory
            in ignored_directories
        ):
            continue

        try:

            chunks = create_code_chunks(
                str(file_path)
            )

            all_chunks.extend(
                chunks
            )

        except SyntaxError as e:

            print(
                f"Skipping {file_path}: "
                f"Syntax error: {e}"
            )

        except Exception as e:

            print(
                f"Skipping {file_path}: "
                f"{e}"
            )

    return all_chunks


def print_code_chunks(
    repository_path: str = "workspace",
):
    """
    Display the generated code chunks.
    """

    chunks = chunk_repository(
        repository_path
    )

    print(
        "\n========================================"
    )

    print(
        "          CODE CHUNKS"
    )

    print(
        "========================================"
    )

    print(
        f"\nTotal chunks: "
        f"{len(chunks)}"
    )

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):

        print(
            "\n----------------------------------------"
        )

        print(
            f"CHUNK {index}"
        )

        print(
            "----------------------------------------"
        )

        print(
            f"ID: "
            f"{chunk['id']}"
        )

        print(
            f"Type: "
            f"{chunk['type']}"
        )

        print(
            f"Name: "
            f"{chunk['name']}"
        )

        print(
            f"File: "
            f"{chunk['file']}"
        )

        print(
            f"Lines: "
            f"{chunk['line_start']}-"
            f"{chunk['line_end']}"
        )

        print(
            "\nCONTENT:"
        )

        print(
            chunk["content"]
        )


if __name__ == "__main__":

    print_code_chunks(
        "workspace"
    )