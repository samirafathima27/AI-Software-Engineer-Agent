from pathlib import Path
import re

from app.llm.client import ask_llm
from app.tools.code_search import search_code


# ============================================================
# REPOSITORY CONFIGURATION
# ============================================================

WORKSPACE_ROOT = Path("workspace").resolve()


# ============================================================
# FILE DISCOVERY
# ============================================================

def get_repository_files() -> list[str]:
    """
    Return the actual Python files that exist inside workspace/.

    The LLM is never treated as the source of truth for file
    existence. The filesystem is the source of truth.
    """

    if not WORKSPACE_ROOT.exists():
        return []

    files = []

    ignored_directories = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
    }

    for path in WORKSPACE_ROOT.rglob("*.py"):

        if any(
            part in ignored_directories
            for part in path.parts
        ):
            continue

        relative_path = path.relative_to(
            Path.cwd()
        )

        files.append(
            str(relative_path).replace("\\", "/")
        )

    return sorted(files)


def get_source_files() -> list[str]:
    """
    Return Python source files excluding tests.
    """

    files = get_repository_files()

    return [
        file
        for file in files
        if "/tests/" not in file.lower()
        and not file.lower().startswith("tests/")
        and not Path(file).name.startswith("test_")
    ]


def get_test_files() -> list[str]:
    """
    Return Python test files.
    """

    files = get_repository_files()

    return [
        file
        for file in files
        if (
            "/tests/" in file.lower()
            or Path(file).name.startswith("test_")
        )
    ]


# ============================================================
# REPOSITORY CONTEXT
# ============================================================

def get_repository_context(
    task: str,
    top_k: int = 8,
) -> str:

    results = search_code(
        query=task,
        top_k=top_k,
        refresh_index=False,
    )

    if not results:
        return "No relevant repository code was found."

    context_parts = []

    for index, result in enumerate(
        results,
        start=1,
    ):

        file_path = str(
            result["file"]
        ).replace("\\", "/")

        context_parts.append(
            f"""
--- RELEVANT CODE {index} ---

Name: {result['name']}
Type: {result['type']}
File: {file_path}
Lines: {result['line_start']}-{result['line_end']}

{result['content']}
"""
        )

    return "\n".join(
        context_parts
    )


# ============================================================
# PATH NORMALIZATION
# ============================================================

def normalize_repository_path(
    candidate: str,
    valid_files: list[str],
) -> str | None:
    """
    Convert an LLM-generated path into an actual repository path.

    Example:

    workspace/sample_project/src/pricing.py

    becomes:

    workspace/sample_project/pricing.py

    if pricing.py uniquely exists in the repository.
    """

    candidate = candidate.strip()

    if not candidate:
        return None

    candidate = candidate.strip(
        "`\"' "
    )

    candidate = candidate.replace(
        "\\",
        "/",
    )

    # Remove accidental leading ./.
    if candidate.startswith("./"):
        candidate = candidate[2:]

    # Direct exact match.
    for valid_file in valid_files:

        if candidate == valid_file:
            return valid_file

    # Case-insensitive exact match.
    candidate_lower = candidate.lower()

    for valid_file in valid_files:

        if candidate_lower == valid_file.lower():
            return valid_file

    # Match by filename if unique.
    candidate_name = Path(candidate).name.lower()

    matches = [
        file
        for file in valid_files
        if Path(file).name.lower() == candidate_name
    ]

    if len(matches) == 1:
        return matches[0]

    return None


def normalize_file_list(
    files: list[str],
    valid_files: list[str],
) -> list[str]:

    normalized = []

    for file in files:

        normalized_path = normalize_repository_path(
            file,
            valid_files,
        )

        if (
            normalized_path
            and normalized_path not in normalized
        ):
            normalized.append(
                normalized_path
            )

    return normalized


# ============================================================
# ANALYSIS OUTPUT PARSER
# ============================================================

def extract_section(
    text: str,
    section_name: str,
    next_sections: list[str],
) -> list[str]:

    pattern = (
        rf"{re.escape(section_name)}:\s*"
        rf"(.*?)(?=\n(?:"
        + "|".join(
            re.escape(section)
            for section in next_sections
        )
        + r"):\s*|\Z)"
    )

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return []

    content = match.group(1).strip()

    lines = []

    for line in content.splitlines():

        line = line.strip()

        if not line:
            continue

        line = re.sub(
            r"^[\-\*\d\.\)\s]+",
            "",
            line,
        )

        if line:
            lines.append(line)

    return lines


def rebuild_analysis(
    original_analysis: str,
    valid_source_files: list[str],
    valid_test_files: list[str],
) -> str:
    """
    Force the FILES and TESTS sections to contain only real
    repository files.
    """

    files = extract_section(
        original_analysis,
        "FILES",
        [
            "CHANGE",
            "TESTS",
            "NEW_TESTS",
        ],
    )

    tests = extract_section(
        original_analysis,
        "TESTS",
        [
            "NEW_TESTS",
        ],
    )

    normalized_files = normalize_file_list(
        files,
        valid_source_files,
    )

    normalized_tests = normalize_file_list(
        tests,
        valid_test_files,
    )

    # Extract task/change/new-tests sections from original response.
    task_match = re.search(
        r"TASK:\s*(.*?)(?=\nFILES:|\Z)",
        original_analysis,
        flags=re.IGNORECASE | re.DOTALL,
    )

    change_match = re.search(
        r"CHANGE:\s*(.*?)(?=\nTESTS:|\nNEW_TESTS:|\Z)",
        original_analysis,
        flags=re.IGNORECASE | re.DOTALL,
    )

    new_tests_match = re.search(
        r"NEW_TESTS:\s*(.*?)(?:\Z)",
        original_analysis,
        flags=re.IGNORECASE | re.DOTALL,
    )

    task_text = (
        task_match.group(1).strip()
        if task_match
        else ""
    )

    change_text = (
        change_match.group(1).strip()
        if change_match
        else ""
    )

    new_tests_text = (
        new_tests_match.group(1).strip()
        if new_tests_match
        else "None"
    )

    if not new_tests_text:
        new_tests_text = "None"

    if not normalized_files:

        # If the LLM completely failed to identify source files,
        # use source files that appeared in retrieved context.
        context_source_candidates = []

        for file in valid_source_files:

            if file in original_analysis:
                context_source_candidates.append(
                    file
                )

        normalized_files = context_source_candidates

    files_text = (
        "\n".join(normalized_files)
        if normalized_files
        else "None"
    )

    tests_text = (
        "\n".join(normalized_tests)
        if normalized_tests
        else "None"
    )

    return f"""TASK: {task_text}

FILES:
{files_text}

CHANGE:
{change_text}

TESTS:
{tests_text}

NEW_TESTS:
{new_tests_text}
"""


# ============================================================
# CODE ANALYSIS
# ============================================================

def analyze_task(
    task: str,
    repository_context: str = "",
) -> str:

    if not repository_context:

        repository_context = get_repository_context(
            task
        )

    all_repository_files = (
        get_repository_files()
    )

    source_files = (
        get_source_files()
    )

    test_files = (
        get_test_files()
    )

    source_inventory = (
        "\n".join(
            f"- {file}"
            for file in source_files
        )
        if source_files
        else "- No source files found."
    )

    test_inventory = (
        "\n".join(
            f"- {file}"
            for file in test_files
        )
        if test_files
        else "- No test files found."
    )

    prompt = f"""
You are the Code Analysis Agent for an autonomous
software engineering system.

The user's actual software repository is:

workspace/

The AI agent framework itself is outside the target
repository.

IMPORTANT:

The filesystem inventory below is authoritative.

You MUST select file paths ONLY from this inventory.

ACTUAL SOURCE FILES:
{source_inventory}

ACTUAL TEST FILES:
{test_inventory}

ALL ACTUAL REPOSITORY FILES:
{chr(10).join("- " + file for file in all_repository_files)}

Never invent a directory.

For example, if the repository contains:

workspace/sample_project/pricing.py

DO NOT output:

workspace/sample_project/src/pricing.py

unless that exact file appears in the inventory.

The retrieved repository code is also authoritative
for understanding the existing implementation.

USER TASK:
{task}

RELEVANT REPOSITORY CODE:
{repository_context}

Your job is to determine exactly which existing
repository source files are affected by the task.

MULTI-FILE RULES:

1. A task may require changes to multiple files.
2. Follow function and class dependencies.
3. If file A calls a function from file B, consider
   whether B's change affects A.
4. Identify every source file that genuinely needs
   modification.
5. Do not include files that do not need changes.
6. Do not put tests inside FILES.
7. Tests must be listed separately.
8. Preserve existing behavior unless the task requires
   changing it.
9. Do not redesign unrelated code.
10. Do not modify the AI agent framework.
11. Do not modify main.py.
12. Do not invent files.
13. Every path in FILES must be copied exactly from
    ACTUAL SOURCE FILES.
14. Every path in TESTS must be copied exactly from
    ACTUAL TEST FILES.
15. If a file is not in the inventory, it cannot be selected.

Return ONLY this format:

TASK: <one sentence>

FILES:
<exact source file path>
<exact source file path if needed>

CHANGE:
<short description of the required changes>

TESTS:
<exact existing test file path>
<exact existing test file path if needed>

NEW_TESTS:
<new tests that should be added if necessary>
"""

    raw_analysis = ask_llm(
        prompt,
        max_tokens=500,
    )

    # --------------------------------------------------------
    # HARD VALIDATION
    # --------------------------------------------------------

    validated_analysis = rebuild_analysis(
        raw_analysis,
        source_files,
        test_files,
    )

    return validated_analysis


# ============================================================
# IMPLEMENTATION GUIDANCE
# ============================================================

def generate_code_guidance(
    task: str,
    repository_context: str = "",
) -> str:

    if not repository_context:

        repository_context = get_repository_context(
            task
        )

    source_files = (
        get_source_files()
    )

    test_files = (
        get_test_files()
    )

    source_inventory = (
        "\n".join(
            f"- {file}"
            for file in source_files
        )
        if source_files
        else "- No source files found."
    )

    test_inventory = (
        "\n".join(
            f"- {file}"
            for file in test_files
        )
        if test_files
        else "- No test files found."
    )

    prompt = f"""
You are the Implementation Planning Agent.

TARGET REPOSITORY:

workspace/

USER TASK:

{task}

ACTUAL SOURCE FILES:

{source_inventory}

ACTUAL TEST FILES:

{test_inventory}

RELEVANT REPOSITORY CODE:

{repository_context}

Give implementation guidance for the coding agent.

STRICT PATH RULE:

Only mention file paths that appear in the
ACTUAL SOURCE FILES or ACTUAL TEST FILES lists.

Never invent paths.

For example:

VALID:
workspace/sample_project/pricing.py

INVALID:
workspace/sample_project/src/pricing.py

Rules:

- Consider dependencies between files.
- Explain which files need changes and why.
- Preserve existing behavior unless the task requires
  changing it.
- Do not modify the AI agent framework.
- Do not modify main.py.
- Do not refactor unrelated code.
- Do not invent requirements.
- Do not invent directories.
- Keep the guidance concise.
- Maximum 8 bullet points.

Return ONLY bullet points.
"""

    guidance = ask_llm(
        prompt,
        max_tokens=400,
    )

    # --------------------------------------------------------
    # Replace accidental invalid paths in guidance.
    # --------------------------------------------------------

    all_valid_files = (
        source_files + test_files
    )

    for candidate in re.findall(
        r"(?:workspace/|workspace\\)[^\s`'\"),:]+",
        guidance,
    ):

        normalized = normalize_repository_path(
            candidate,
            all_valid_files,
        )

        if normalized:
            guidance = guidance.replace(
                candidate,
                normalized,
            )

    return guidance


# ============================================================
# RAG + CODE AGENT
# ============================================================

def analyze_task_with_rag(
    task: str,
    top_k: int = 8,
) -> dict:

    repository_context = get_repository_context(
        task,
        top_k=top_k,
    )

    analysis = analyze_task(
        task,
        repository_context,
    )

    guidance = generate_code_guidance(
        task,
        repository_context,
    )

    return {
        "task": task,
        "repository_context": repository_context,
        "analysis": analysis,
        "guidance": guidance,
    }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print(
        "\n========================================"
    )

    print(
        "        RAG CODE AGENT TEST"
    )

    print(
        "========================================"
    )

    print(
        "\nActual repository files:"
    )

    for file in get_repository_files():

        print(
            f"  - {file}"
        )

    task = input(
        "\nEnter a software task: "
    ).strip()

    if not task:

        print(
            "No task provided."
        )

        raise SystemExit

    result = analyze_task_with_rag(
        task,
        top_k=8,
    )

    print(
        "\n========================================"
    )

    print(
        "       RETRIEVED CODE"
    )

    print(
        "========================================"
    )

    print(
        result["repository_context"]
    )

    print(
        "\n========================================"
    )

    print(
        "       VALIDATED CODE AGENT ANALYSIS"
    )

    print(
        "========================================"
    )

    print(
        result["analysis"]
    )

    print(
        "\n========================================"
    )

    print(
        "       IMPLEMENTATION GUIDANCE"
    )

    print(
        "========================================"
    )

    print(
        result["guidance"]
    )