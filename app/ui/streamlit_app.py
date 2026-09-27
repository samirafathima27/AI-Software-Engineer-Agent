import sys
from pathlib import Path
from uuid import uuid4
import zipfile

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.graph.workflow import run_workflow, resume_workflow
from app.tools.git_tools import git_branch


WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
UPLOAD_ROOT = WORKSPACE_ROOT / "user_projects"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_MB = 50
BLOCKED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
}
BLOCKED_SUFFIXES = {".pem", ".key"}
BLOCKED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
}


st.set_page_config(
    page_title="AI Software Engineer",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .stApp { background:#080b12; color:#e5e7eb; }
    .main .block-container {
        max-width:1400px;
        padding-top:2.5rem;
        padding-bottom:4rem;
    }
    [data-testid="stSidebar"] {
        background:#0b0f17;
        border-right:1px solid #1e293b;
    }
    h1,h2,h3,h4 { color:#f8fafc !important; }
    p,label { color:#94a3b8; }
    textarea {
        background:#0b1018 !important;
        color:#e2e8f0 !important;
        border:1px solid #334155 !important;
        border-radius:10px !important;
    }
    .stButton > button {
        min-height:44px;
        border-radius:9px;
        border:1px solid #293548;
        background:#111827;
        color:#e2e8f0;
        font-weight:600;
    }
    button[kind="primary"] {
        background:linear-gradient(135deg,#6366f1,#7c3aed) !important;
        border:none !important;
        color:white !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background:#0d121b;
        border:1px solid #202b3b;
        border-radius:14px;
    }
    [data-testid="stMetric"] {
        background:#0d121b;
        border:1px solid #202b3b;
        border-radius:12px;
        padding:1rem;
    }
    [data-testid="stMetricLabel"] { color:#64748b !important; }
    [data-testid="stMetricValue"] { color:#f8fafc !important; }
    [data-testid="stExpander"] {
        background:#0d121b;
        border:1px solid #202b3b;
        border-radius:10px;
    }
    hr { border-color:#1e293b !important; }
    #MainMenu, footer { visibility:hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


defaults = {
    "workflow_result": None,
    "thread_id": None,
    "approval_pending": False,
    "approval_data": None,
    "task": "",
    "project_path": None,
    "project_name": None,
    "project_source": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def normalize_workflow_response(response):
    if isinstance(response, tuple) and len(response) >= 2:
        return response[0], response[1]

    if isinstance(response, dict):
        if "thread_id" in response and "result" in response:
            return response["thread_id"], response["result"]
        return None, response

    return None, {
        "status": "completed",
        "tests_passed": False,
        "iteration": 0,
        "implementation_results": [],
        "test_result": "",
        "debug_result": "",
        "review_result": "",
        "workflow_output": str(response),
    }


def extract_interrupt_data(result):
    if not isinstance(result, dict):
        return None

    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None

    first = interrupts[0]

    if hasattr(first, "value"):
        return first.value

    if isinstance(first, dict):
        return first

    return None


def reset_workflow():
    st.session_state.workflow_result = None
    st.session_state.thread_id = None
    st.session_state.approval_pending = False
    st.session_state.approval_data = None


def reset_project():
    reset_workflow()
    st.session_state.project_path = None
    st.session_state.project_name = None
    st.session_state.project_source = None


def is_blocked_member(name: str) -> bool:
    normalized = name.replace("\\", "/").strip("/")
    if not normalized:
        return True

    parts = Path(normalized).parts

    if any(part in BLOCKED_DIRS for part in parts):
        return True

    filename = parts[-1]
    if filename in BLOCKED_NAMES:
        return True

    if any(filename.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
        return True

    return False


def safe_extract_zip(
    uploaded_file,
    destination: Path,
) -> tuple[Path, int, int]:
    """Safely extract a ZIP and return project root, files, skipped count."""

    if uploaded_file.size and uploaded_file.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(
            f"ZIP is too large. Maximum allowed size is {MAX_UPLOAD_MB} MB."
        )

    destination.mkdir(parents=True, exist_ok=False)

    extracted = 0
    skipped = 0

    with zipfile.ZipFile(uploaded_file) as archive:
        for info in archive.infolist():
            raw_name = info.filename.replace("\\", "/")

            if not raw_name or raw_name.endswith("/"):
                continue

            if is_blocked_member(raw_name):
                skipped += 1
                continue

            parts = Path(raw_name).parts

            if any(part in {"", ".", ".."} for part in parts):
                raise ValueError(
                    f"Unsafe ZIP path detected: {info.filename}"
                )

            # Reject Unix symlink entries.
            unix_mode = (info.external_attr >> 16) & 0o170000
            if unix_mode == 0o120000:
                skipped += 1
                continue

            target = (destination / Path(*parts)).resolve()

            try:
                target.relative_to(destination.resolve())
            except ValueError as exc:
                raise ValueError(
                    f"Unsafe ZIP path detected: {info.filename}"
                ) from exc

            target.parent.mkdir(parents=True, exist_ok=True)

            with archive.open(info) as source, target.open("wb") as output:
                output.write(source.read())

            extracted += 1

    if extracted == 0:
        raise ValueError(
            "The ZIP does not contain any usable project files."
        )

    # If the ZIP contains exactly one top-level directory, use it as
    # the project root. Otherwise use the extraction directory itself.
    children = list(destination.iterdir())

    if len(children) == 1 and children[0].is_dir():
        root = children[0]
    else:
        root = destination

    return root.resolve(), extracted, skipped


def handle_upload(uploaded_file):
    reset_project()

    upload_id = uuid4().hex[:12]
    destination = UPLOAD_ROOT / upload_id

    try:
        root, extracted, skipped = safe_extract_zip(
            uploaded_file,
            destination,
        )

        st.session_state.project_path = str(root)
        st.session_state.project_name = root.name
        st.session_state.project_source = uploaded_file.name

        st.success(
            f"Project loaded: **{root.name}** · "
            f"{extracted} files extracted"
            + (f" · {skipped} skipped" if skipped else "")
        )

    except Exception:
        if destination.exists():
            import shutil
            shutil.rmtree(destination, ignore_errors=True)
        raise


try:
    branch = git_branch()
except Exception:
    branch = "unknown"


with st.sidebar:
    st.title("◈ AI Software Engineer")
    st.caption("Autonomous repository engineering agent")

    st.divider()

    st.subheader("Workflow")

    steps = [
        ("1", "Understand", "Read repository context"),
        ("2", "Plan", "Identify required changes"),
        ("3", "Approve", "Human review checkpoint"),
        ("4", "Implement", "Modify source code"),
        ("5", "Test", "Generate and run tests"),
        ("6", "Debug", "Fix failures automatically"),
        ("7", "Review", "Final engineering review"),
    ]

    for number, name, description in steps:
        st.markdown(f"**{number}. {name}**")
        st.caption(description)

    st.divider()
    st.subheader("Project")

    if st.session_state.project_path:
        st.write(
            f"**Loaded:** `{st.session_state.project_name}`"
        )
        st.caption(st.session_state.project_path)
    else:
        st.write("**Loaded:** Demo project")
        st.caption("workspace/sample_project")

    st.divider()
    st.caption("ZIP Upload · RAG · LangGraph · Multi-Agent · Pytest")


header_left, header_right = st.columns(
    [5, 1],
    vertical_alignment="center",
)

with header_left:
    st.title("◈ AI Software Engineer")
    st.write(
        "Upload a project ZIP, describe a software task, and let the "
        "agent inspect, plan, implement, test, debug and review the change."
    )

with header_right:
    st.success("● AGENT ONLINE")


m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric(
        "Project",
        st.session_state.project_name or "Demo",
    )

with m2:
    st.metric("Git Branch", branch)

with m3:
    st.metric("Architecture", "Multi-Agent")

with m4:
    st.metric("Testing", "Pytest")


st.write("")

upload_col, project_col = st.columns(
    [2, 1],
    gap="large",
)

with upload_col:
    with st.container(border=True):
        st.caption("PROJECT INPUT")
        st.subheader("Upload your repository")

        uploaded = st.file_uploader(
            "Upload a ZIP containing your software project",
            type=["zip"],
            help=(
                f"Maximum ZIP size: {MAX_UPLOAD_MB} MB. "
                "Sensitive files such as .env, .pem and .key are skipped."
            ),
        )

        if uploaded is not None:
            upload_key = f"{uploaded.name}:{uploaded.size}"

            if st.session_state.get("_last_upload_key") != upload_key:
                try:
                    handle_upload(uploaded)
                    st.session_state["_last_upload_key"] = upload_key
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not load project: {exc}")

with project_col:
    with st.container(border=True):
        st.caption("CURRENT PROJECT")
        st.subheader(
            st.session_state.project_name or "Built-in demo"
        )

        if st.session_state.project_path:
            st.success("User project loaded")
            st.caption(
                "The agent will operate only inside this project."
            )

            if st.button(
                "Remove uploaded project",
                use_container_width=True,
            ):
                reset_project()
                st.session_state["_last_upload_key"] = None
                st.rerun()
        else:
            st.info(
                "No ZIP uploaded. The built-in sample project will be used."
            )


st.write("")

task_column, capability_column = st.columns(
    [2, 1],
    gap="large",
)

with task_column:
    with st.container(border=True):
        st.caption("SOFTWARE TASK")
        st.subheader("What should the agent build or fix?")

        task = st.text_area(
            "Task",
            value=st.session_state.task,
            placeholder=(
                "Example:\n"
                "Add a 5% service fee after applying discounts "
                "and update the tests accordingly."
            ),
            height=170,
            label_visibility="collapsed",
        )

        st.session_state.task = task

        run_col, clear_col = st.columns([3, 1])

        with run_col:
            run_clicked = st.button(
                "Run AI Engineer  →",
                type="primary",
                use_container_width=True,
            )

        with clear_col:
            clear_clicked = st.button(
                "Clear",
                use_container_width=True,
            )

        if clear_clicked:
            reset_workflow()
            st.session_state.task = ""
            st.rerun()


with capability_column:
    with st.container(border=True):
        st.caption("ENGINEERING PIPELINE")
        st.subheader("What the agent does")

        st.markdown(
            """
**🔍 Understand**  
Indexes and retrieves relevant repository code.

**🧠 Plan**  
Identifies the files and changes required.

**👤 Approve**  
Pauses before source-code modification.

**⚙️ Implement**  
Generates the requested source changes.

**🧪 Test**  
Generates and executes pytest tests.

**🔄 Debug**  
Diagnoses failures and attempts fixes.

**🔎 Review**  
Performs a final engineering review.
"""
        )


if run_clicked:
    if not task.strip():
        st.warning("Please describe the software task first.")
    else:
        reset_workflow()

        selected_project = (
            st.session_state.project_path
            or str(WORKSPACE_ROOT / "sample_project")
        )

        with st.status(
            "AI Software Engineer is working...",
            expanded=True,
        ) as status:
            try:
                st.write("🔍 Indexing selected project...")
                st.write("🧠 Retrieving relevant code with RAG...")
                st.write("📋 Analyzing requested changes...")
                st.write("🗂️ Preparing implementation plan...")

                raw_response = run_workflow(
                    task.strip(),
                    project_path=selected_project,
                    approval_required=True,
                )

                thread_id, result = normalize_workflow_response(
                    raw_response
                )

                st.session_state.thread_id = thread_id

                approval_data = extract_interrupt_data(result)

                if approval_data is not None:
                    st.session_state.approval_data = approval_data
                    st.session_state.approval_pending = True

                    status.update(
                        label="Waiting for your approval",
                        state="complete",
                    )
                else:
                    st.session_state.workflow_result = result
                    status.update(
                        label="Workflow completed",
                        state="complete",
                    )

            except Exception as exc:
                status.update(
                    label="Workflow failed",
                    state="error",
                )

                st.error(f"Workflow error: {exc}")

                with st.expander("Technical error details"):
                    st.exception(exc)


if st.session_state.approval_pending:
    st.write("")

    with st.container(border=True):
        st.caption("HUMAN APPROVAL REQUIRED")
        st.subheader("Review proposed changes")

        approval_data = st.session_state.approval_data or {}

        project_path = approval_data.get(
            "project_path",
            st.session_state.project_path or "",
        )

        target_files = approval_data.get("target_files", [])
        planned_test_files = approval_data.get("planned_test_files", [])
        approval_files = approval_data.get(
            "approval_files",
            target_files + planned_test_files,
        )
        guidance = approval_data.get("guidance", "")
        message = approval_data.get("message", "")

        st.write("**Project:**")
        st.code(project_path, language="text")

        if approval_files:
            st.write("**The agent proposes changes to:**")

            for file_name in approval_files:
                st.code(file_name, language="text")

        if message:
            st.info(message)

        if guidance:
            with st.expander(
                "View implementation plan",
                expanded=True,
            ):
                st.markdown(guidance)

        approve_col, reject_col = st.columns(2)

        with approve_col:
            approve_clicked = st.button(
                "✓ Approve & Continue",
                type="primary",
                use_container_width=True,
            )

        with reject_col:
            reject_clicked = st.button(
                "✕ Reject Changes",
                use_container_width=True,
            )

        if approve_clicked:
            with st.status(
                "AI Engineer is implementing and testing...",
                expanded=True,
            ) as status:
                try:
                    st.write("⚙️ Implementing approved changes...")
                    st.write("🧪 Generating and running tests...")
                    st.write("🔄 Checking for failures...")
                    st.write("🔎 Running final review...")

                    raw_response = resume_workflow(
                        st.session_state.thread_id,
                        approved=True,
                    )

                    returned_thread_id, result = (
                        normalize_workflow_response(raw_response)
                    )

                    if returned_thread_id:
                        st.session_state.thread_id = returned_thread_id

                    next_approval = extract_interrupt_data(result)

                    if next_approval is not None:
                        st.session_state.approval_data = next_approval
                        st.session_state.approval_pending = True

                        status.update(
                            label="Another approval is required",
                            state="complete",
                        )
                    else:
                        st.session_state.workflow_result = result
                        st.session_state.approval_pending = False
                        st.session_state.approval_data = None

                        status.update(
                            label="Workflow completed",
                            state="complete",
                        )

                        st.rerun()

                except Exception as exc:
                    status.update(
                        label="Workflow failed",
                        state="error",
                    )
                    st.error(f"Workflow error: {exc}")

                    with st.expander("Technical error details"):
                        st.exception(exc)

        if reject_clicked:
            try:
                result = resume_workflow(
                    st.session_state.thread_id,
                    approved=False,
                )

                st.session_state.workflow_result = result
                st.session_state.approval_pending = False
                st.session_state.approval_data = None

                st.rerun()

            except Exception as exc:
                st.error(f"Workflow error: {exc}")


result = st.session_state.workflow_result

if result:
    st.write("")
    st.divider()

    st.caption("ENGINEERING RESULT")
    st.subheader("Agent execution complete")

    _, result = normalize_workflow_response(result)

    tests_passed = bool(result.get("tests_passed", False))
    status_value = str(result.get("status", "unknown"))
    iteration = result.get("iteration", 0)
    implementation_results = result.get(
        "implementation_results",
        [],
    )
    changed_files = result.get("changed_files", [])
    file_changes = result.get("file_changes", [])

    if tests_passed:
        st.success(
            "✓ Build completed successfully — "
            "implementation verified and tests passed."
        )
    else:
        st.warning(
            "⚠ Workflow completed, but verification did not pass."
        )

    result_col1, result_col2, result_col3, result_col4 = st.columns(4)

    with result_col1:
        st.metric("Status", status_value)

    with result_col2:
        st.metric(
            "Tests",
            "PASSED" if tests_passed else "FAILED",
        )

    with result_col3:
        st.metric("Debug Iterations", iteration)

    with result_col4:
        st.metric(
            "Files Changed",
            len(changed_files)
            if isinstance(changed_files, list)
            else 0,
        )

    st.write("")

    activity_col, files_col = st.columns(
        [1, 1],
        gap="large",
    )

    with activity_col:
        with st.container(border=True):
            st.caption("AGENT ACTIVITY")
            st.subheader("Execution summary")

            st.markdown(
                """
✓ Repository context retrieved

✓ Relevant code identified with RAG

✓ Implementation plan generated

✓ Human approval checkpoint completed

✓ Source changes implemented

✓ Automated tests executed

✓ Final code review completed
"""
            )

    with files_col:
        with st.container(border=True):
            st.caption("SOURCE CHANGES")
            st.subheader("Files touched")

            if changed_files:
                for file_name in changed_files:
                    st.code(file_name, language="text")
            else:
                st.caption("No files were changed.")

    if file_changes:
        st.write("")
        with st.expander("📝 Source and test changes", expanded=False):
            import difflib

            for change in file_changes:
                if not change.get("changed"):
                    continue

                file_name = change.get("file", "Unknown file")
                category = change.get("category", "file")
                before = str(change.get("before", ""))
                after = str(change.get("after", ""))

                st.markdown(f"**{file_name}** · `{category}`")
                diff = "\n".join(
                    difflib.unified_diff(
                        before.splitlines(),
                        after.splitlines(),
                        fromfile=f"a/{file_name}",
                        tofile=f"b/{file_name}",
                        lineterm="",
                    )
                )
                st.code(diff or "No textual difference.", language="diff")

    test_result = result.get("test_result", "")

    if test_result:
        st.write("")
        with st.expander(
            "🧪 Test execution output",
            expanded=False,
        ):
            st.code(str(test_result), language="text")

    debug_result = result.get("debug_result", "")

    if debug_result:
        st.write("")
        with st.expander(
            "🔄 Debugging information",
            expanded=False,
        ):
            st.markdown(str(debug_result))

    review_result = result.get("review_result", "")

    if review_result:
        st.write("")

        with st.container(border=True):
            st.caption("FINAL REVIEW")
            st.subheader("Code review")
            st.markdown(str(review_result))

    with st.expander(
        "Technical workflow output",
        expanded=False,
    ):
        st.code(str(result), language="python")


st.write("")
st.divider()

st.caption(
    "AI Software Engineer · RAG · LangGraph · "
    "Multi-Agent Systems · Automated Testing"
)
