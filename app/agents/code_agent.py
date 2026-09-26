from app.llm.client import ask_llm
from app.tools.code_search import search_code


def get_repository_context(
    task: str,
    top_k: int = 5
) -> str:

    results = search_code(
        query=task,
        top_k=top_k,
        refresh_index=False
    )

    if not results:
        return "No relevant repository code was found."

    context_parts = []

    for index, result in enumerate(
        results,
        start=1
    ):

        context_parts.append(
            f"""
--- RELEVANT CODE {index} ---

Name: {result['name']}
Type: {result['type']}
File: {result['file']}
Lines: {result['line_start']}-{result['line_end']}

{result['content']}
"""
        )

    return "\n".join(
        context_parts
    )


def analyze_task(
    task: str,
    repository_context: str = ""
) -> str:

    if not repository_context:

        repository_context = get_repository_context(
            task
        )

    prompt = f"""
You are the Code Analysis Agent for an autonomous
software engineering system.

The user's actual software repository is inside:

workspace/

The AI agent framework itself is outside the target
repository.

IMPORTANT:
Never modify:
- main.py
- app/
- data/
- logs/

Only files inside workspace/ may be modified.

USER TASK:
{task}

RELEVANT REPOSITORY CODE:
{repository_context}

Your job is to determine exactly which repository
source files are affected by the task.

IMPORTANT MULTI-FILE RULES:

1. A task may require changes to multiple files.
2. Follow function and class dependencies.
3. If file A calls a function from file B, consider
   whether B's change affects A.
4. Identify every source file that genuinely needs
   modification.
5. Do not include files that do not need changes.
6. Do not modify tests in the FILES section.
7. Tests should be identified separately.
8. Preserve existing behavior unless the task requires
   changing it.
9. Do not redesign unrelated code.
10. Use the retrieved repository code as the source of truth.
11. Do not invent files that do not exist unless the task
    explicitly requires creating a new file.

Return ONLY this format:

TASK: <one sentence>

FILES:
<workspace file 1>
<workspace file 2>
<workspace file 3 if needed>

CHANGE:
<short description of the required changes across the files>

TESTS:
<existing test files that must be updated or affected>

NEW_TESTS:
<new tests that should be added if necessary>
"""

    return ask_llm(
        prompt,
        max_tokens=400
    )


def generate_code_guidance(
    task: str,
    repository_context: str = ""
) -> str:

    if not repository_context:

        repository_context = get_repository_context(
            task
        )

    prompt = f"""
You are the Implementation Planning Agent.

TARGET REPOSITORY:
workspace/

USER TASK:
{task}

RELEVANT REPOSITORY CODE:
{repository_context}

Give implementation guidance for the coding agent.

Rules:

- Consider dependencies between files.
- Explain which files need changes and why.
- Preserve existing behavior unless the task requires
  changing it.
- Do not modify the AI agent framework.
- Do not modify main.py.
- Do not refactor unrelated code.
- Do not invent requirements.
- Keep the guidance concise.
- Maximum 8 bullet points.

Return ONLY bullet points.
"""

    return ask_llm(
        prompt,
        max_tokens=350
    )


def analyze_task_with_rag(
    task: str,
    top_k: int = 5
) -> dict:

    repository_context = get_repository_context(
        task,
        top_k=top_k
    )

    analysis = analyze_task(
        task,
        repository_context
    )

    guidance = generate_code_guidance(
        task,
        repository_context
    )

    return {
        "task": task,
        "repository_context": repository_context,
        "analysis": analysis,
        "guidance": guidance,
    }


if __name__ == "__main__":

    print("\n========================================")
    print("        RAG CODE AGENT TEST")
    print("========================================")

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
        top_k=5
    )

    print("\n========================================")
    print("       RETRIEVED CODE")
    print("========================================")

    print(
        result["repository_context"]
    )

    print("\n========================================")
    print("       CODE AGENT ANALYSIS")
    print("========================================")

    print(
        result["analysis"]
    )

    print("\n========================================")
    print("       IMPLEMENTATION GUIDANCE")
    print("========================================")

    print(
        result["guidance"]
    )