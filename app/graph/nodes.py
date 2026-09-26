from pathlib import Path

from langgraph.types import interrupt

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

from app.graph.state import AgentState


TEST_DIRECTORY = "workspace/sample_project"

WORKSPACE_ROOT = Path(
    "workspace"
).resolve()


# ============================================================
# INITIALIZE
# ============================================================

def initialize_node(
    state: AgentState
) -> AgentState:

    print(
        "\n========================================"
    )

    print(
        "LANGGRAPH: INITIALIZE"
    )

    print(
        "========================================"
    )

    print(
        f"\nTask: {state['task']}"
    )

    state["iteration"] = 0

    state["max_iterations"] = (
        state.get(
            "max_iterations",
            3
        )
    )

    state["status"] = "running"

    state["tests_passed"] = False

    state["approval_granted"] = False

    return state


# ============================================================
# INDEX
# ============================================================

def index_node(
    state: AgentState
) -> AgentState:

    print(
        "\n========================================"
    )

    print(
        "LANGGRAPH: INDEX REPOSITORY"
    )

    print(
        "========================================"
    )

    count = index_repository(
        "workspace"
    )

    print(
        f"\nIndexed {count} code chunks."
    )

    return state


# ============================================================
# RETRIEVE
# ============================================================

def retrieve_node(
    state: AgentState
) -> AgentState:

    print(
        "\n========================================"
    )

    print(
        "LANGGRAPH: RETRIEVE CODE"
    )

    print(
        "========================================"
    )

    context = get_repository_context(
        state["task"],
        top_k=8,
    )

    state["repository_context"] = context

    print(
        "\nRelevant repository code:"
    )

    print(
        context
    )

    return state


# ============================================================
# ANALYZE
# ============================================================

def analyze_node(
    state: AgentState
) -> AgentState:

    print(
        "\n========================================"
    )

    print(
        "LANGGRAPH: CODE ANALYSIS"
    )

    print(
        "========================================"
    )

    plan = analyze_task(
        state["task"],
        state["repository_context"],
    )

    state["plan"] = plan

    print(
        "\nCODE AGENT PLAN:"
    )

    print(
        plan
    )

    return state


# ============================================================
# EXTRACT TARGET FILES
# ============================================================

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


# ============================================================
# PLAN
# ============================================================

def plan_node(
    state: AgentState
) -> AgentState:

    print(
        "\n========================================"
    )

    print(
        "LANGGRAPH: IMPLEMENTATION PLAN"
    )

    print(
        "========================================"
    )

    target_files = extract_target_files(
        state["plan"]
    )

    guidance = generate_code_guidance(
        state["task"],
        state["repository_context"],
    )

    state["target_files"] = target_files

    state["guidance"] = guidance

    print(
        "\nTarget files:"
    )

    for file_path in target_files:

        print(
            f"  - {file_path}"
        )

    print(
        "\nImplementation guidance:"
    )

    print(
        guidance
    )

    return state


# ============================================================
# HUMAN APPROVAL
# ============================================================

def approval_node(
    state: AgentState
) -> AgentState:

    if not state.get(
        "approval_required",
        True
    ):

        state["approval_granted"] = True

        return state

    if not state.get(
        "target_files"
    ):

        state["approval_granted"] = True

        return state

    approval_message = f"""
The AI Software Engineer wants to modify:

{chr(10).join(
    f"  - {file_path}"
    for file_path in state["target_files"]
)}

TASK:
{state["task"]}

IMPLEMENTATION GUIDANCE:
{state["guidance"]}

Approve these source-code changes?
"""

    state["approval_message"] = (
        approval_message
    )

    decision = interrupt(
        {
            "type": "code_change_approval",
            "message": approval_message,
            "task": state["task"],
            "target_files": state["target_files"],
            "guidance": state["guidance"],
        }
    )

    if isinstance(
        decision,
        dict
    ):

        approved = decision.get(
            "approved",
            False
        )

    else:

        approved = bool(
            decision
        )

    state["approval_granted"] = (
        approved
    )

    if approved:

        state["status"] = "approved"

    else:

        state["status"] = "cancelled"

    return state


# ============================================================
# WORKSPACE SECURITY
# ============================================================

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


# ============================================================
# CLEAN LLM CODE
# ============================================================

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


# ============================================================
# IMPLEMENT ONE FILE
# ============================================================

def implement_file(
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

    return {
        "status": "success",
        "changed": (
            current_code
            != final_code
        ),
        "before": current_code,
        "after": final_code,
    }


# ============================================================
# IMPLEMENT
# ============================================================

def implement_node(
    state: AgentState
) -> AgentState:

    print(
        "\n========================================"
    )

    print(
        "LANGGRAPH: IMPLEMENTATION"
    )

    print(
        "========================================"
    )

    if not state.get(
        "approval_granted",
        False
    ):

        print(
            "\nImplementation cancelled."
        )

        return state

    target_files = state.get(
        "target_files",
        []
    )

    results = []

    for file_path in target_files:

        print(
            f"\nModifying: {file_path}"
        )

        result = implement_file(
            task=state["task"],
            file_path=file_path,
            guidance=state["guidance"],
        )

        results.append({
            "file": file_path,
            "result": result,
        })

        print(
            result
        )

    state["implementation_results"] = (
        results
    )

    return state


# ============================================================
# REFRESH RAG
# ============================================================

def refresh_index_node(
    state: AgentState
) -> AgentState:

    print(
        "\n========================================"
    )

    print(
        "LANGGRAPH: REFRESH RAG"
    )

    print(
        "========================================"
    )

    count = index_repository(
        "workspace"
    )

    print(
        f"\nRe-indexed {count} code chunks."
    )

    return state


# ============================================================
# FIND TEST FILE
# ============================================================

def find_test_file(
    target_file: str
) -> str:

    path = Path(
        target_file
    )

    current = path.parent

    while True:

        tests_dir = (
            current / "tests"
        )

        if tests_dir.is_dir():

            return str(
                tests_dir
                / f"test_{path.stem}.py"
            ).replace(
                "\\",
                "/"
            )

        if current == current.parent:

            break

        current = current.parent

    return str(
        path.parent
        / "tests"
        / f"test_{path.stem}.py"
    ).replace(
        "\\",
        "/"
    )


# ============================================================
# TEST AGENT
# ============================================================

def test_node(
    state: AgentState
) -> AgentState:

    print(
        "\n========================================"
    )

    print(
        "LANGGRAPH: TEST AGENT"
    )

    print(
        "========================================"
    )

    target_files = state.get(
        "target_files",
        []
    )

    test_files = []

    for target_file in target_files:

        test_file = find_test_file(
            target_file
        )

        if test_file not in test_files:

            test_files.append(
                test_file
            )

    for test_file in test_files:

        try:

            current_test_code = read_file(
                test_file
            )

        except Exception:

            current_test_code = ""

        print(
            f"\nGenerating tests for: "
            f"{test_file}"
        )

        generated_tests = generate_tests(
            task=state["task"],
            repository_context=state[
                "repository_context"
            ],
            target_files=target_files,
            test_file=test_file,
            current_test_code=current_test_code,
        )

        generated_tests = (
            clean_code_response(
                generated_tests
            )
        )

        if not generated_tests:

            raise ValueError(
                "Test Agent returned empty "
                f"code for {test_file}"
            )

        write_file(
            test_file,
            generated_tests
        )

    state["test_files"] = test_files

    return state


# ============================================================
# RUN PYTEST
# ============================================================

def run_tests_node(
    state: AgentState
) -> AgentState:

    print(
        "\n========================================"
    )

    print(
        "LANGGRAPH: RUN TESTS"
    )

    print(
        "========================================"
    )

    result = run_pytest(
        TEST_DIRECTORY
    )

    state["test_result"] = result

    state["tests_passed"] = (
        "Exit code: 0"
        in result
    )

    print(
        result
    )

    return state


# ============================================================
# DEBUG FILE EXTRACTION
# ============================================================

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


# ============================================================
# DEBUG
# ============================================================

def debug_node(
    state: AgentState
) -> AgentState:

    print(
        "\n========================================"
    )

    print(
        "LANGGRAPH: DEBUG AGENT"
    )

    print(
        "========================================"
    )

    state["iteration"] = (
        state.get(
            "iteration",
            0
        ) + 1
    )

    print(
        f"\nDebug iteration: "
        f"{state['iteration']}/"
        f"{state.get('max_iterations', 3)}"
    )

    debug_context = get_repository_context(
        state["task"],
        top_k=8,
    )

    debug_result = diagnose_failure(
        state["task"],
        debug_context,
        state["test_result"],
    )

    state["debug_result"] = debug_result

    print(
        "\nDEBUG DIAGNOSIS:"
    )

    print(
        debug_result
    )

    source_files = extract_debug_files(
        debug_result,
        "SOURCE_FILES"
    )

    test_files = extract_debug_files(
        debug_result,
        "TEST_FILES"
    )

    state["debug_source_files"] = (
        source_files
    )

    state["debug_test_files"] = (
        test_files
    )

    implementations = []

    # --------------------------------------------------------
    # APPLY SOURCE FIXES
    # --------------------------------------------------------

    for file_path in source_files:

        print(
            f"\nApplying debug fix to: "
            f"{file_path}"
        )

        result = implement_file(
            task=state["task"],
            file_path=file_path,
            guidance=debug_result,
        )

        implementations.append({
            "file": file_path,
            "result": result,
        })

        print(
            result
        )

    state["debug_implementations"] = (
        implementations
    )

    # --------------------------------------------------------
    # REGENERATE TEST FILES
    # --------------------------------------------------------

    for test_file in test_files:

        try:

            current_test_code = read_file(
                test_file
            )

        except Exception:

            current_test_code = ""

        regenerated_tests = generate_tests(
            task=state["task"],
            repository_context=debug_context,
            target_files=(
                source_files
                or state.get(
                    "target_files",
                    []
                )
            ),
            test_file=test_file,
            current_test_code=current_test_code,
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

    return state


# ============================================================
# REVIEW
# ============================================================

def review_node(
    state: AgentState
) -> AgentState:

    print(
        "\n========================================"
    )

    print(
        "LANGGRAPH: REVIEW AGENT"
    )

    print(
        "========================================"
    )

    final_context = get_repository_context(
        state["task"],
        top_k=8,
    )

    review = review_changes(
        state["task"],
        final_context,
        state.get(
            "test_result",
            ""
        ),
    )

    state["review_result"] = review

    if state.get(
        "tests_passed",
        False
    ):

        state["status"] = "success"

    else:

        state["status"] = "tests_failed"

    print(
        review
    )

    return state


# ============================================================
# FINALIZE
# ============================================================

def finalize_node(
    state: AgentState
) -> AgentState:

    if state.get(
        "status"
    ) == "cancelled":

        print(
            "\nWorkflow cancelled by user."
        )

        return state

    if state.get(
        "tests_passed",
        False
    ):

        state["status"] = "success"

    return state


# ============================================================
# ROUTE AFTER APPROVAL
# ============================================================

def route_after_approval(
    state: AgentState
) -> str:

    if state.get(
        "status"
    ) == "cancelled":

        return "finalize"

    return "implement"


# ============================================================
# ROUTE AFTER TESTS
# ============================================================

def route_after_tests(
    state: AgentState
) -> str:

    if state.get(
        "tests_passed",
        False
    ):

        return "review"

    return "debug"


# ============================================================
# ROUTE AFTER DEBUG
# ============================================================

def route_after_debug(
    state: AgentState
) -> str:

    iteration = state.get(
        "iteration",
        0
    )

    maximum = state.get(
        "max_iterations",
        3
    )

    if state.get(
        "tests_passed",
        False
    ):

        return "review"

    if iteration >= maximum:

        print(
            "\nMaximum debug iterations reached."
        )

        return "review"

    return "refresh"