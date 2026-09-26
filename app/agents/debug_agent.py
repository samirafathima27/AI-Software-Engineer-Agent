from app.llm.client import ask_llm


def diagnose_failure(
    task: str,
    repository_context: str,
    test_output: str
) -> str:

    prompt = f"""
You are the Debug Agent for an autonomous
software engineering system.

USER TASK:
{task}

REPOSITORY:
{repository_context}

TEST/ERROR OUTPUT:
{test_output}

Your job is to diagnose the actual test failure and
determine the smallest safe correction.

IMPORTANT:

1. Read the test failure carefully.
2. Identify the actual root cause.
3. Understand which source files are involved.
4. Understand which tests are affected.
5. Do not assume that a failing test means the new
   implementation is wrong.
6. If the requested behavior intentionally changes the
   expected result, the tests may need to be updated.
7. Preserve unrelated behavior.
8. Do not redesign the application.
9. Do not modify the AI agent framework.
10. Only recommend changes inside workspace/.

Return ONLY:

ROOT_CAUSE:
<actual root cause>

SOURCE_FILES:
<workspace source files that require correction, one per line>

TEST_FILES:
<workspace test files that require correction, one per line>

FIX:
<smallest safe correction>

VERIFICATION:
<what should be run to verify the fix>
"""

    return ask_llm(
        prompt,
        max_tokens=500
    )


def generate_fix_guidance(
    task,
    repository_context,
    test_output
):

    return diagnose_failure(
        task,
        repository_context,
        test_output
    )