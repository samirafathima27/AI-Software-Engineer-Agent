from pathlib import Path
import re

from langgraph.types import interrupt

from app.agents.code_agent import (
    analyze_task,
    generate_code_guidance,
    get_repository_context,
)
from app.agents.debug_agent import diagnose_failure
from app.agents.review_agent import review_changes
from app.agents.test_agent import generate_tests, clean_code_response
from app.retrieval.indexer import index_repository
from app.tools.file_tools import read_file, write_file
from app.tools.test_tools import run_pytest
from app.llm.client import ask_llm
from app.graph.state import AgentState


WORKSPACE_ROOT = Path("workspace").resolve()


def display_path(state: AgentState, file_path: str | Path) -> str:
    """Return a stable project-relative path for UI/state output."""
    root = project_root(state)
    path = Path(file_path).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"Path is outside the selected project: {file_path}"
        ) from exc
    return relative.as_posix()


def record_file_change(
    state: AgentState,
    file_path: str | Path,
    category: str,
    before: str,
    after: str,
) -> None:
    """Track the final before/after state of a file changed during this run."""
    relative = display_path(state, file_path)
    changed = before != after

    changed_files = state.setdefault("changed_files", [])
    if changed and relative not in changed_files:
        changed_files.append(relative)

    changes = state.setdefault("file_changes", [])
    for item in changes:
        if item.get("file") == relative:
            item["after"] = after
            item["changed"] = item.get("before", before) != after
            item["category"] = category
            if not item["changed"] and relative in changed_files:
                changed_files.remove(relative)
            elif item["changed"] and relative not in changed_files:
                changed_files.append(relative)
            return

    changes.append({
        "file": relative,
        "category": category,
        "before": before,
        "after": after,
        "changed": changed,
    })


def clean_repository_context(context: str) -> str:
    """Normalize paths and remove duplicated chunk metadata from RAG output."""
    if not context:
        return context

    normalized = context.replace("\\", "/")

    # The retrieval layer already exposes Name/Type/File/Lines. Some indexed
    # chunks also contain the same metadata in their text, so remove that
    # second metadata block before sending context to the LLM.
    metadata_pattern = re.compile(
        r"(Name: [^\n]+\nType: [^\n]+\nFile: [^\n]+\nLines: [^\n]+\n\n)"
        r"(?:Type: [^\n]+\nName: [^\n]+\nFile: [^\n]+\nLines: [^\n]+\n\n)"
    )
    return metadata_pattern.sub(r"\1", normalized)


def project_root(state: AgentState) -> Path:
    raw = state.get("project_path")
    if not raw:
        return (WORKSPACE_ROOT / "sample_project").resolve()

    root = Path(raw).resolve()

    try:
        root.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise ValueError(
            f"Project must be inside workspace/: {raw}"
        ) from exc

    if not root.exists() or not root.is_dir():
        raise ValueError(f"Project directory does not exist: {root}")

    return root


def project_relative_path(
    state: AgentState,
    file_path: str,
) -> str:
    """Resolve an LLM-produced path against the selected project."""
    root = project_root(state)
    raw = file_path.strip().replace("\\", "/")

    candidate = Path(raw)

    # Already an absolute path.
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        # Repository/RAG paths are normally workspace/... .
        if raw.startswith("workspace/"):
            resolved = Path(raw).resolve()
        else:
            resolved = (root / raw).resolve()

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"Agent attempted to access a file outside the selected project: "
            f"{file_path}"
        ) from exc

    return str(resolved).replace("\\", "/")


def initialize_node(state: AgentState) -> AgentState:
    root = project_root(state)

    print("\n========================================")
    print("LANGGRAPH: INITIALIZE")
    print("========================================")
    print(f"\nTask: {state['task']}")
    print(f"Project: {root}")

    state["project_path"] = str(root)
    state["iteration"] = 0
    state["max_iterations"] = state.get("max_iterations", 3)
    state["status"] = "running"
    state["tests_passed"] = False
    state["approval_granted"] = False
    state["implementation_results"] = []
    state["test_results"] = []
    state["changed_files"] = []
    state["file_changes"] = []

    return state


def index_node(state: AgentState) -> AgentState:
    root = project_root(state)

    print("\n========================================")
    print("LANGGRAPH: INDEX REPOSITORY")
    print("========================================")

    count = index_repository(str(root))
    print(f"\nIndexed {count} code chunks.")

    return state


def retrieve_node(state: AgentState) -> AgentState:
    print("\n========================================")
    print("LANGGRAPH: RETRIEVE CODE")
    print("========================================")

    context = clean_repository_context(
        get_repository_context(state["task"], top_k=8)
    )
    state["repository_context"] = context

    print("\nRelevant repository code:")
    print(context)

    return state


def analyze_node(state: AgentState) -> AgentState:
    print("\n========================================")
    print("LANGGRAPH: CODE ANALYSIS")
    print("========================================")

    plan = analyze_task(
        state["task"],
        state["repository_context"],
    )
    state["plan"] = plan

    print("\nCODE AGENT PLAN:")
    print(plan)

    return state


def extract_target_files(
    plan: str,
    state: AgentState,
) -> list[str]:
    lines = plan.splitlines()
    files: list[str] = []
    collecting = False

    for line in lines:
        stripped = line.strip()

        if stripped.upper() == "FILES:":
            collecting = True
            continue

        if not collecting or not stripped:
            continue

        upper = stripped.upper()

        if (
            upper.startswith("CHANGE:")
            or upper.startswith("TESTS:")
            or upper.startswith("NEW_TESTS:")
        ):
            break

        try:
            normalized = project_relative_path(state, stripped)
        except ValueError:
            continue

        if normalized not in files:
            files.append(normalized)

    return files


def extract_planned_test_files(
    plan: str,
    state: AgentState,
) -> list[str]:
    """Extract files listed under the TESTS: section of the plan."""
    lines = plan.splitlines()
    files: list[str] = []
    collecting = False

    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()

        if upper == "TESTS:":
            collecting = True
            continue

        if not collecting:
            continue

        if upper.startswith("NEW_TESTS:"):
            break

        if not stripped:
            continue

        try:
            normalized = project_relative_path(state, stripped)
        except ValueError:
            continue

        if normalized not in files:
            files.append(normalized)

    return files


def plan_node(state: AgentState) -> AgentState:
    print("\n========================================")
    print("LANGGRAPH: IMPLEMENTATION PLAN")
    print("========================================")

    target_files = extract_target_files(state["plan"], state)
    planned_test_files = extract_planned_test_files(state["plan"], state)
    approval_files = []
    for file_path in target_files + planned_test_files:
        if file_path not in approval_files:
            approval_files.append(file_path)

    guidance = generate_code_guidance(
        state["task"],
        state["repository_context"],
    )

    state["target_files"] = target_files
    state["planned_test_files"] = planned_test_files
    state["approval_files"] = approval_files
    state["guidance"] = guidance

    print("\nTarget files:")
    for file_path in approval_files:
        print(f"  - {file_path}")

    print("\nImplementation guidance:")
    print(guidance)

    return state


def approval_node(state: AgentState) -> AgentState:
    if not state.get("approval_required", True):
        state["approval_granted"] = True
        return state

    if not state.get("target_files"):
        state["approval_granted"] = True
        return state

    approval_message = f"""
The AI Software Engineer proposes changes to:

{chr(10).join(f"  - {file_path}" for file_path in state.get("approval_files", state["target_files"]))}

TASK:
{state["task"]}

IMPLEMENTATION GUIDANCE:
{state["guidance"]}

Approve these source-code changes?
"""

    state["approval_message"] = approval_message

    decision = interrupt(
        {
            "type": "code_change_approval",
            "message": approval_message,
            "task": state["task"],
            "project_path": state["project_path"],
            "target_files": state["target_files"],
            "planned_test_files": state.get("planned_test_files", []),
            "approval_files": state.get("approval_files", []),
            "guidance": state["guidance"],
        }
    )

    approved = (
        decision.get("approved", False)
        if isinstance(decision, dict)
        else bool(decision)
    )

    state["approval_granted"] = approved
    state["status"] = "approved" if approved else "cancelled"

    return state


def validate_project_file(
    state: AgentState,
    file_path: str,
) -> Path:
    root = project_root(state)
    path = Path(project_relative_path(state, file_path)).resolve()

    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"File outside selected project is not allowed: {file_path}"
        ) from exc

    return path


def clean_llm_code(code: str) -> str:
    code = code.strip()

    if code.startswith("```"):
        lines = code.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        code = "\n".join(lines).strip()

    return code


def implement_file(
    state: AgentState,
    task: str,
    file_path: str,
    guidance: str,
) -> dict:
    path = validate_project_file(state, file_path)
    normalized_path = str(path).replace("\\", "/")

    if not path.exists():
        return {
            "status": "error",
            "message": f"Target file does not exist: {normalized_path}",
        }

    current_code = read_file(normalized_path, allowed_root=project_root(state))

    prompt = f"""
You are the Implementation Agent.

USER TASK:
{task}

TARGET FILE:
{normalized_path}

CURRENT FILE CONTENT:
{current_code}

IMPLEMENTATION GUIDANCE:
{guidance}

Implement the requested functionality.

Rules:
- Modify ONLY this target file.
- Preserve existing functionality unless the task requires changing it.
- Make the smallest safe change.
- Do not modify unrelated code.
- Do not invent requirements.
- Follow the implementation guidance.
- Preserve the existing coding style.
- If the requested functionality already exists correctly, return the current file unchanged.
- Return ONLY the complete updated file.
- Do not use markdown code fences.
- Do not explain anything.
"""

    try:
        updated_code = ask_llm(prompt, max_tokens=900).strip()
    except Exception as exc:
        return {
            "status": "error",
            "message": f"LLM implementation failed: {exc}",
        }

    updated_code = clean_llm_code(updated_code)

    if not updated_code:
        return {
            "status": "error",
            "message": "LLM returned empty code.",
        }

    write_result = write_file(
        normalized_path,
        updated_code,
        allowed_root=project_root(state),
    )

    if write_result.startswith("Error:"):
        return {
            "status": "error",
            "message": write_result,
        }

    final_code = read_file(
        normalized_path,
        allowed_root=project_root(state),
    )

    record_file_change(
        state,
        normalized_path,
        "source",
        current_code,
        final_code,
    )

    return {
        "status": "success",
        "changed": current_code != final_code,
        "before": current_code,
        "after": final_code,
        "file": display_path(state, normalized_path),
    }


def implement_node(state: AgentState) -> AgentState:
    print("\n========================================")
    print("LANGGRAPH: IMPLEMENTATION")
    print("========================================")

    if not state.get("approval_granted", False):
        print("\nImplementation cancelled.")
        return state

    results = []

    for file_path in state.get("target_files", []):
        print(f"\nModifying: {file_path}")

        result = implement_file(
            state=state,
            task=state["task"],
            file_path=file_path,
            guidance=state["guidance"],
        )

        results.append({"file": file_path, "result": result})
        print(result)

    state["implementation_results"] = results
    return state


def refresh_index_node(state: AgentState) -> AgentState:
    root = project_root(state)

    print("\n========================================")
    print("LANGGRAPH: REFRESH RAG")
    print("========================================")

    count = index_repository(str(root))
    print(f"\nRe-indexed {count} code chunks.")

    return state


def find_test_file(target_file: str) -> str:
    path = Path(target_file)
    current = path.parent

    while True:
        tests_dir = current / "tests"

        if tests_dir.is_dir():
            return str(
                tests_dir / f"test_{path.stem}.py"
            ).replace("\\", "/")

        if current == current.parent:
            break

        current = current.parent

    return str(
        path.parent / "tests" / f"test_{path.stem}.py"
    ).replace("\\", "/")


def test_node(state: AgentState) -> AgentState:
    print("\n========================================")
    print("LANGGRAPH: TEST AGENT")
    print("========================================")

    target_files = state.get("target_files", [])
    test_files: list[str] = list(state.get("planned_test_files", []))

    for target_file in target_files:
        test_file = find_test_file(target_file)

        try:
            test_file = project_relative_path(state, test_file)
        except ValueError:
            continue

        if test_file not in test_files:
            test_files.append(test_file)

    for test_file in test_files:
        try:
            current_test_code = read_file(
                test_file,
                allowed_root=project_root(state),
            )
        except Exception:
            current_test_code = ""

        print(f"\nGenerating tests for: {test_file}")

        generated_tests = generate_tests(
            task=state["task"],
            repository_context=state["repository_context"],
            target_files=target_files,
            test_file=test_file,
            current_test_code=current_test_code,
        )

        generated_tests = clean_code_response(generated_tests)

        if not generated_tests:
            raise ValueError(
                f"Test Agent returned empty code for {test_file}"
            )

        write_result = write_file(
            test_file,
            generated_tests,
            allowed_root=project_root(state),
        )

        if write_result.startswith("Error:"):
            raise ValueError(write_result)

        final_test_code = read_file(
            test_file,
            allowed_root=project_root(state),
        )
        test_change = {
            "file": display_path(state, test_file),
            "changed": current_test_code != final_test_code,
            "before": current_test_code,
            "after": final_test_code,
        }
        state.setdefault("test_results", []).append(test_change)
        record_file_change(
            state,
            test_file,
            "test",
            current_test_code,
            final_test_code,
        )

    state["test_files"] = test_files
    return state


def run_tests_node(state: AgentState) -> AgentState:
    root = project_root(state)

    print("\n========================================")
    print("LANGGRAPH: RUN TESTS")
    print("========================================")

    result = run_pytest(
        str(root),
        allowed_root=root,
    )

    state["test_result"] = result
    state["tests_passed"] = "Exit code: 0" in result

    print(result)
    return state


def extract_debug_files(
    debug_result: str,
    section_name: str,
    state: AgentState,
) -> list[str]:
    lines = debug_result.splitlines()
    files: list[str] = []
    collecting = False

    for line in lines:
        stripped = line.strip()

        if stripped.upper() == f"{section_name.upper()}:":
            collecting = True
            continue

        if not collecting or not stripped:
            continue

        if stripped.upper() in {
            "SOURCE_FILES:",
            "TEST_FILES:",
            "FIX:",
            "VERIFICATION:",
        }:
            break

        try:
            normalized = project_relative_path(state, stripped)
        except ValueError:
            continue

        if normalized not in files:
            files.append(normalized)

    return files


def debug_node(state: AgentState) -> AgentState:
    print("\n========================================")
    print("LANGGRAPH: DEBUG AGENT")
    print("========================================")

    state["iteration"] = state.get("iteration", 0) + 1

    print(
        f"\nDebug iteration: {state['iteration']}/"
        f"{state.get('max_iterations', 3)}"
    )

    debug_context = clean_repository_context(
        get_repository_context(
            state["task"],
            top_k=8,
        )
    )

    debug_result = diagnose_failure(
        state["task"],
        debug_context,
        state["test_result"],
    )

    state["debug_result"] = debug_result

    print("\nDEBUG DIAGNOSIS:")
    print(debug_result)

    source_files = extract_debug_files(
        debug_result,
        "SOURCE_FILES",
        state,
    )
    test_files = extract_debug_files(
        debug_result,
        "TEST_FILES",
        state,
    )

    state["debug_source_files"] = source_files
    state["debug_test_files"] = test_files

    implementations = []

    for file_path in source_files:
        print(f"\nApplying debug fix to: {file_path}")

        result = implement_file(
            state=state,
            task=state["task"],
            file_path=file_path,
            guidance=debug_result,
        )

        implementations.append({
            "file": file_path,
            "result": result,
        })

        print(result)

    state["debug_implementations"] = implementations

    for test_file in test_files:
        try:
            current_test_code = read_file(
                test_file,
                allowed_root=project_root(state),
            )
        except Exception:
            current_test_code = ""

        regenerated_tests = generate_tests(
            task=state["task"],
            repository_context=debug_context,
            target_files=source_files or state.get("target_files", []),
            test_file=test_file,
            current_test_code=current_test_code,
        )

        regenerated_tests = clean_code_response(regenerated_tests)

        if regenerated_tests:
            write_result = write_file(
                test_file,
                regenerated_tests,
                allowed_root=project_root(state),
            )
            if write_result.startswith("Error:"):
                raise ValueError(write_result)

            final_test_code = read_file(
                test_file,
                allowed_root=project_root(state),
            )
            record_file_change(
                state,
                test_file,
                "test",
                current_test_code,
                final_test_code,
            )

    return state


def review_node(state: AgentState) -> AgentState:
    print("\n========================================")
    print("LANGGRAPH: REVIEW AGENT")
    print("========================================")

    final_context = clean_repository_context(
        get_repository_context(
            state["task"],
            top_k=8,
        )
    )

    review = review_changes(
        state["task"],
        final_context,
        state.get("test_result", ""),
    )

    state["review_result"] = review
    state["status"] = (
        "success" if state.get("tests_passed", False)
        else "tests_failed"
    )

    print(review)
    return state


def finalize_node(state: AgentState) -> AgentState:
    if state.get("status") == "cancelled":
        print("\nWorkflow cancelled by user.")
        return state

    if state.get("tests_passed", False):
        state["status"] = "success"

    return state


def route_after_approval(state: AgentState) -> str:
    if state.get("status") == "cancelled":
        return "finalize"
    return "implement"


def route_after_tests(state: AgentState) -> str:
    return "review" if state.get("tests_passed", False) else "debug"


def route_after_debug(state: AgentState) -> str:
    iteration = state.get("iteration", 0)
    maximum = state.get("max_iterations", 3)

    if state.get("tests_passed", False):
        return "review"

    if iteration >= maximum:
        print("\nMaximum debug iterations reached.")
        return "review"

    return "refresh"
