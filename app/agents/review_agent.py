from app.llm.client import ask_llm


def review_changes(
    task: str,
    repository_context: str,
    test_output: str
) -> str:

    prompt = f"""
You are the Review Agent.

USER TASK:
{task}

REPOSITORY:
{repository_context}

TEST RESULT:
{test_output}

Review whether the implementation satisfies the user's request.

Check:
1. Does it implement the requested behavior?
2. Were unrelated changes introduced?
3. Is existing behavior unnecessarily changed?
4. Did the tests pass?
5. Are there obvious bugs?

Do NOT give a numerical score or ranking.

Return:
- Implementation status
- Problems found
- Required corrections, if any
- Final review summary
"""

    return ask_llm(prompt)