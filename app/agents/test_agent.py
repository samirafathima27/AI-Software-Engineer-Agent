from app.llm.client import ask_llm


def generate_tests(
    task: str,
    repository_context: str,
    target_files: list[str],
    test_file: str,
    current_test_code: str = "",
) -> str:

    target_files_text = "\n".join(
        f"- {file_path}"
        for file_path in target_files
    )

    prompt = f"""
You are the Test Agent for an autonomous
software engineering system.

USER TASK:
{task}

TARGET SOURCE FILES:
{target_files_text}

TEST FILE TO UPDATE:
{test_file}

RELEVANT REPOSITORY CODE:
{repository_context}

CURRENT TEST FILE:
{current_test_code}

Your job is to create or update the pytest test file.

IMPORTANT:

1. Preserve all existing tests.
2. Do not remove tests merely because expected behavior
   changed.
3. If the user task changes expected behavior, update the
   expected values accordingly.
4. Add tests for the new functionality.
5. Consider dependencies between all target source files.
6. Test the behavior from the public entry point where
   appropriate.
7. Do not test internal implementation details unnecessarily.
8. Keep the existing testing style.
9. Import functions/classes using the repository's existing
   package structure.
10. Return the COMPLETE test file.
11. Return valid Python only.
12. Do not use markdown code fences.
13. Do not explain anything.

The updated test file must remain compatible with pytest.

Return ONLY the complete updated test file.
"""

    return ask_llm(
        prompt,
        max_tokens=900
    ).strip()


def clean_code_response(
    response: str
) -> str:

    response = response.strip()

    if response.startswith("```"):

        lines = response.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        response = "\n".join(
            lines
        ).strip()

    return response