from pathlib import Path

from app.agents.code_agent import (
    analyze_task,
    generate_code_guidance,
    get_repository_context,
)

from app.agents.debug_agent import (
    diagnose_failure,
)

from app.agents.review_agent import (
    review_changes,
)

from app.agents.test_agent import (
    generate_tests,
    clean_code_response,
)

from app.retrieval.indexer import (
    index_repository,
)

from app.tools.file_tools import (
    read_file,
    write_file,
)

from app.tools.test_tools import (
    run_pytest,
)

from app.llm.client import (
    ask_llm,
)


WORKSPACE_ROOT = Path(
    "workspace"
).resolve()


TEST_DIRECTORY = (
    "workspace/sample_project"
)


def get_task_mode(
    task: str
) -> str:

    task_lower = task.lower()

    if any(
        keyword in task_lower
        for keyword in [
            "fix",
            "bug",
            "error",
            "debug",
            "issue",
            "broken",
        ]
    ):
        return "debug"

    if any(
        keyword in task_lower
        for keyword in [
            "add",
            "create",
            "implement",
            "build",
            "develop",
            "support",
        ]
    ):
        return "implementation"

    if any(
        keyword in task_lower
        for keyword in [
            "test",
            "testing",
        ]
    ):
        return "testing"

    return "general"


def extract_target_files(
    plan: str
) -> list[str]:

    lines = plan.splitlines()

    files = []

    collecting = False

    for line in lines:

        stripped = line.strip()

        if stripped.upper() == "FILES:":

            collecting = True
            continue

        if not collecting:
            continue

        if not stripped:
            continue

        upper_line = stripped.upper()

        if (
            upper_line.startswith("CHANGE:")
            or upper_line.startswith("TESTS:")
            or upper_line.startswith("NEW_TESTS:")
        ):
            break

        if (
            stripped.startswith("workspace/")
            or stripped.startswith("workspace\\")
        ):

            normalized = stripped.replace(
                "\\",
                "/"
            )

            if normalized not in files:
                files.append(
                    normalized
                )

    return files


def extract_debug_files(
    debug_result: str,
    section_name: str
) -> list[str]:

    lines = debug_result.splitlines()

    files = []

    collecting = False

    for line in lines:

        stripped = line.strip()

        if (
            stripped.upper()
            == f"{section_name.upper()}:"
        ):

            collecting = True
            continue

        if not collecting:
            continue

        if not stripped:
            continue

        upper_line = stripped.upper()

        if upper_line in {
            "SOURCE_FILES:",
            "TEST_FILES:",
            "FIX:",
            "VERIFICATION:",
        }:

            break

        if (
            stripped.startswith("workspace/")
            or stripped.startswith("workspace\\")
        ):

            normalized = stripped.replace(
                "\\",
                "/"
            )

            if normalized not in files:

                files.append(
                    normalized
                )

    return files


def validate_workspace_file(
    file_path: str
) -> Path:

    path = Path(
        file_path
    ).resolve()

    try:

        path.relative_to(
            WORKSPACE_ROOT
        )

    except ValueError:

        raise ValueError(
            "File outside workspace is not allowed: "
            f"{file_path}"
        )

    return path


def clean_llm_code(
    code: str
) -> str:

    code = code.strip()

    if code.startswith("```"):

        lines = code.splitlines()

        if (
            lines
            and lines[0].startswith("```")
        ):

            lines = lines[1:]

        if (
            lines
            and lines[-1].strip() == "```"
        ):

            lines = lines[:-1]

        code = "\n".join(
            lines
        ).strip()

    return code


def apply_code_change(
    task: str,
    file_path: str,
    guidance: str,
) -> dict:

    path = validate_workspace_file(
        file_path
    )

    if not path.exists():

        return {
            "status": "error",
            "message": (
                "Target file does not exist: "
                f"{file_path}"
            ),
        }

    current_code = read_file(
        file_path
    )

    prompt = f"""
You are the Implementation Agent.

USER TASK:
{task}

TARGET FILE:
{file_path}

CURRENT FILE CONTENT:
{current_code}

IMPLEMENTATION GUIDANCE:
{guidance}

Implement the requested functionality.

Rules:

- Modify ONLY this target file.
- Preserve existing functionality unless the task requires
  changing it.
- Make the smallest safe change.
- Do not modify unrelated code.
- Do not invent requirements.
- Follow the implementation guidance.
- Preserve the existing coding style.
- If the requested functionality already exists correctly,
  return the current file unchanged.
- Return ONLY the complete updated file.
- Do not use markdown code fences.
- Do not explain anything.
"""

    try:

        updated_code = ask_llm(
            prompt,
            max_tokens=900
        ).strip()

    except Exception as e:

        return {
            "status": "error",
            "message": (
                f"LLM implementation failed: {e}"
            ),
        }

    updated_code = clean_llm_code(
        updated_code
    )

    if not updated_code:

        return {
            "status": "error",
            "message": (
                "LLM returned empty code."
            ),
        }

    write_file(
        file_path,
        updated_code
    )

    final_code = read_file(
        file_path
    )

    changed = (
        current_code
        != final_code
    )

    return {
        "status": "success",
        "changed": changed,
        "before": current_code,
        "after": final_code,
    }


def apply_multiple_code_changes(
    task: str,
    target_files: list[str],
    guidance: str,
) -> list[dict]:

    results = []

    for file_path in target_files:

        print(
            "\n----------------------------------------"
        )

        print(
            f"MODIFYING: {file_path}"
        )

        print(
            "----------------------------------------"
        )

        result = apply_code_change(
            task=task,
            file_path=file_path,
            guidance=guidance,
        )

        results.append({
            "file": file_path,
            "result": result,
        })

        if (
            result["status"]
            != "success"
        ):

            print(
                f"\nFailed to modify "
                f"{file_path}: "
                f"{result['message']}"
            )

        elif result["changed"]:

            print(
                f"\nSuccessfully modified: "
                f"{file_path}"
            )

        else:

            print(
                f"\nNo change required: "
                f"{file_path}"
            )

    return results


def find_project_root(
    target_file: str
) -> Path:

    path = Path(
        target_file
    ).resolve()

    current = path.parent

    while True:

        tests_directory = (
            current / "tests"
        )

        if tests_directory.is_dir():

            return current

        if current == current.parent:
            break

        current = current.parent

    return path.parent


def get_test_file(
    target_file: str
) -> str:

    target_path = Path(
        target_file
    )

    project_root = find_project_root(
        target_file
    )

    test_directory = (
        project_root / "tests"
    )

    test_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    test_file = (
        test_directory
        / f"test_{target_path.stem}.py"
    )

    return str(
        test_file
    ).replace(
        "\\",
        "/"
    )


def generate_and_write_tests(
    task: str,
    repository_context: str,
    target_files: list[str],
) -> dict:

    test_files = []

    for target_file in target_files:

        test_file = get_test_file(
            target_file
        )

        if test_file not in test_files:

            test_files.append(
                test_file
            )

    print(
        "\nAffected test files:"
    )

    for test_file in test_files:

        print(
            f"  - {test_file}"
        )

    results = []

    for test_file in test_files:

        try:

            current_test_code = read_file(
                test_file
            )

        except Exception:

            current_test_code = ""

        print(
            "\nGenerating tests for: "
            f"{test_file}"
        )

        try:

            generated_tests = generate_tests(
                task=task,
                repository_context=repository_context,
                target_files=target_files,
                test_file=test_file,
                current_test_code=current_test_code,
            )

        except Exception as e:

            return {
                "status": "error",
                "message": (
                    f"Test Agent failed: {e}"
                ),
            }

        generated_tests = clean_code_response(
            generated_tests
        )

        if not generated_tests:

            return {
                "status": "error",
                "message": (
                    "Test Agent returned empty "
                    f"code for {test_file}."
                ),
            }

        write_file(
            test_file,
            generated_tests
        )

        results.append(
            test_file
        )

    return {
        "status": "success",
        "test_files": results,
    }


def run_autonomous_agent(
    task: str
) -> dict:

    print(
        "\n========================================"
    )

    print(
        "      AI SOFTWARE ENGINEER AGENT"
    )

    print(
        "========================================"
    )

    print(
        "\nUSER TASK:"
    )

    print(
        task
    )

    mode = get_task_mode(
        task
    )

    print(
        f"\nTASK MODE: {mode}"
    )

    # -------------------------------------
    # STEP 1
    # -------------------------------------

    print(
        "\n========================================"
    )

    print(
        "     STEP 1: REPOSITORY INDEXING"
    )

    print(
        "========================================"
    )

    indexed_count = index_repository(
        "workspace"
    )

    print(
        f"\nIndexed {indexed_count} "
        "code chunks."
    )

    # -------------------------------------
    # STEP 2
    # -------------------------------------

    print(
        "\n========================================"
    )

    print(
        "     STEP 2: RAG REPOSITORY SEARCH"
    )

    print(
        "========================================"
    )

    repository_context = (
        get_repository_context(
            task,
            top_k=8
        )
    )

    print(
        "\nRelevant repository code:"
    )

    print(
        repository_context
    )

    # -------------------------------------
    # STEP 3
    # -------------------------------------

    print(
        "\n========================================"
    )

    print(
        "     STEP 3: CODE AGENT ANALYSIS"
    )

    print(
        "========================================"
    )

    plan = analyze_task(
        task,
        repository_context
    )

    print(
        "\nCODE AGENT PLAN:"
    )

    print(
        plan
    )

    target_files = (
        extract_target_files(
            plan
        )
    )

    if not target_files:

        return {
            "status": "failed",
            "reason": (
                "Code Agent did not provide "
                "valid workspace target files."
            ),
            "plan": plan,
        }

    print(
        "\nTarget files:"
    )

    for file_path in target_files:

        print(
            f"  - {file_path}"
        )

    # -------------------------------------
    # STEP 4
    # -------------------------------------

    print(
        "\n========================================"
    )

    print(
        "     STEP 4: IMPLEMENTATION GUIDANCE"
    )

    print(
        "========================================"
    )

    guidance = (
        generate_code_guidance(
            task,
            repository_context
        )
    )

    print(
        guidance
    )

    # -------------------------------------
    # STEP 5
    # -------------------------------------

    print(
        "\n========================================"
    )

    print(
        "     STEP 5: APPLYING CODE CHANGES"
    )

    print(
        "========================================"
    )

    implementations = (
        apply_multiple_code_changes(
            task=task,
            target_files=target_files,
            guidance=guidance,
        )
    )

    failed_implementations = [
        item
        for item in implementations
        if item["result"]["status"]
        != "success"
    ]

    if failed_implementations:

        return {
            "status": "failed",
            "reason": (
                "One or more source files "
                "could not be modified."
            ),
            "plan": plan,
            "implementations": implementations,
        }

    # -------------------------------------
    # STEP 6
    # -------------------------------------

    print(
        "\n========================================"
    )

    print(
        "     STEP 6: REFRESHING RAG INDEX"
    )

    print(
        "========================================"
    )

    indexed_count = index_repository(
        "workspace"
    )

    print(
        f"\nRe-indexed {indexed_count} "
        "code chunks."
    )

    # -------------------------------------
    # STEP 7
    # -------------------------------------

    print(
        "\n========================================"
    )

    print(
        "     STEP 7: TEST AGENT"
    )

    print(
        "========================================"
    )

    test_context = (
        get_repository_context(
            task,
            top_k=8
        )
    )

    test_result = (
        generate_and_write_tests(
            task=task,
            repository_context=test_context,
            target_files=target_files,
        )
    )

    if test_result["status"] != "success":

        return {
            "status": "failed",
            "reason": test_result["message"],
            "target_files": target_files,
        }

    test_files = (
        test_result["test_files"]
    )

    print(
        "\nTest files updated:"
    )

    for test_file in test_files:

        print(
            f"  - {test_file}"
        )

    # -------------------------------------
    # STEP 8
    # -------------------------------------

    print(
        "\n========================================"
    )

    print(
        "     STEP 8: RUNNING TESTS"
    )

    print(
        "========================================"
    )

    pytest_result = run_pytest(
        TEST_DIRECTORY
    )

    print(
        pytest_result
    )

    # -------------------------------------
    # STEP 9
    # DEBUG
    # -------------------------------------

    if "Exit code: 0" not in pytest_result:

        print(
            "\n========================================"
        )

        print(
            "     STEP 9: DEBUG AGENT"
        )

        print(
            "========================================"
        )

        debug_context = (
            get_repository_context(
                task,
                top_k=8
            )
        )

        debug_result = diagnose_failure(
            task,
            debug_context,
            pytest_result
        )

        print(
            "\nDEBUG AGENT:"
        )

        print(
            debug_result
        )

        debug_source_files = (
            extract_debug_files(
                debug_result,
                "SOURCE_FILES"
            )
        )

        debug_test_files = (
            extract_debug_files(
                debug_result,
                "TEST_FILES"
            )
        )

        if debug_source_files:

            print(
                "\nDebug source files:"
            )

            for file_path in debug_source_files:

                print(
                    f"  - {file_path}"
                )

            print(
                "\nApplying debug source fixes..."
            )

            debug_implementations = (
                apply_multiple_code_changes(
                    task=task,
                    target_files=debug_source_files,
                    guidance=debug_result,
                )
            )

        if debug_test_files:

            print(
                "\nApplying debug test fixes..."
            )

            for test_file in debug_test_files:

                try:

                    current_test_code = (
                        read_file(
                            test_file
                        )
                    )

                except Exception:

                    current_test_code = ""

                regenerated_tests = (
                    generate_tests(
                        task=task,
                        repository_context=debug_context,
                        target_files=(
                            debug_source_files
                            or target_files
                        ),
                        test_file=test_file,
                        current_test_code=current_test_code,
                    )
                )

                regenerated_tests = (
                    clean_code_response(
                        regenerated_tests
                    )
                )

                if regenerated_tests:

                    write_file(
                        test_file,
                        regenerated_tests
                    )

        print(
            "\nRe-running tests..."
        )

        pytest_result = run_pytest(
            TEST_DIRECTORY
        )

        print(
            pytest_result
        )

    else:

        print(
            "\nAll tests passed. "
            "Debug Agent not required."
        )

    # -------------------------------------
    # STEP 10
    # -------------------------------------

    print(
        "\n========================================"
    )

    print(
        "     STEP 10: FINAL RAG REFRESH"
    )

    print(
        "========================================"
    )

    final_index_count = (
        index_repository(
            "workspace"
        )
    )

    print(
        f"\nFinal indexed chunks: "
        f"{final_index_count}"
    )

    # -------------------------------------
    # STEP 11
    # -------------------------------------

    print(
        "\n========================================"
    )

    print(
        "     STEP 11: REVIEW AGENT"
    )

    print(
        "========================================"
    )

    final_context = (
        get_repository_context(
            task,
            top_k=8
        )
    )

    review_result = review_changes(
        task,
        final_context,
        pytest_result
    )

    print(
        review_result
    )

    success = (
        "Exit code: 0"
        in pytest_result
    )

    # -------------------------------------
    # FINAL
    # -------------------------------------

    print(
        "\n========================================"
    )

    print(
        "           FINAL RESULT"
    )

    print(
        "========================================"
    )

    if success:

        print(
            "STATUS: SUCCESS"
        )

    else:

        print(
            "STATUS: TESTS FAILED"
        )

    print(
        "\nModified files:"
    )

    for file_path in target_files:

        print(
            f"  - {file_path}"
        )

    print(
        "\nTest files:"
    )

    for test_file in test_files:

        print(
            f"  - {test_file}"
        )

    return {
        "status": (
            "success"
            if success
            else "tests_failed"
        ),
        "task": task,
        "target_files": target_files,
        "test_files": test_files,
        "plan": plan,
        "guidance": guidance,
        "test_result": pytest_result,
        "review": review_result,
    }


if __name__ == "__main__":

    print(
        "\n========================================"
    )

    print(
        "      AUTONOMOUS CODING MODE"
    )

    print(
        "========================================"
    )

    task = input(
        "\nEnter a software task: "
    ).strip()

    if not task:

        print(
            "No task provided."
        )

        raise SystemExit

    result = run_autonomous_agent(
        task
    )

    print(
        "\n========================================"
    )

    print(
        "        AGENT EXECUTION COMPLETE"
    )

    print(
        "========================================"
    )

    print(
        f"\nStatus: "
        f"{result['status']}"
    )