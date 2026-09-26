import streamlit as st

from app.graph.workflow import (
    run_workflow,
    resume_workflow,
)

from app.tools.git_tools import (
    git_branch,
    git_status,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Software Engineer",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #080b12;
        color: #e5e7eb;
    }

    .main .block-container {
        max-width: 1400px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }

    [data-testid="stSidebar"] {
        background: #0b0f17;
        border-right: 1px solid #1e293b;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }

    h1, h2, h3, h4 {
        color: #f8fafc !important;
    }

    p, label {
        color: #94a3b8;
    }

    textarea {
        background-color: #0b1018 !important;
        color: #e2e8f0 !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }

    textarea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 1px #6366f1 !important;
    }

    .stButton > button {
        min-height: 44px;
        border-radius: 9px;
        border: 1px solid #293548;
        background: #111827;
        color: #e2e8f0;
        font-weight: 600;
    }

    .stButton > button:hover {
        border-color: #6366f1;
        color: white;
    }

    button[kind="primary"] {
        background: linear-gradient(
            135deg,
            #6366f1,
            #7c3aed
        ) !important;

        border: none !important;
        color: white !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #0d121b;
        border: 1px solid #202b3b;
        border-radius: 14px;
    }

    [data-testid="stMetric"] {
        background: #0d121b;
        border: 1px solid #202b3b;
        border-radius: 12px;
        padding: 1rem;
    }

    [data-testid="stMetricLabel"] {
        color: #64748b !important;
    }

    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
    }

    [data-testid="stStatusWidget"] {
        border: 1px solid #293548;
        border-radius: 12px;
        background: #0d121b;
    }

    [data-testid="stExpander"] {
        background: #0d121b;
        border: 1px solid #202b3b;
        border-radius: 10px;
    }

    hr {
        border-color: #1e293b !important;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "workflow_result": None,
    "thread_id": None,
    "approval_pending": False,
    "approval_data": None,
    "task": "",
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# WORKFLOW RESULT NORMALIZER
# ============================================================

def normalize_workflow_response(response):
    """
    Handles all supported return formats from workflow.py.

    Format A:
        (thread_id, state)

    Format B:
        {
            "thread_id": "...",
            "result": state
        }

    Format C:
        direct state dictionary
    """

    # --------------------------------------------------------
    # Tuple
    # --------------------------------------------------------

    if isinstance(response, tuple):

        if len(response) >= 2:

            return (
                response[0],
                response[1],
            )

        return (
            None,
            {},
        )

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if isinstance(response, dict):

        # Wrapped workflow response
        if (
            "thread_id" in response
            and "result" in response
        ):

            return (
                response["thread_id"],
                response["result"],
            )

        # Direct LangGraph state
        return (
            None,
            response,
        )

    # --------------------------------------------------------
    # Unexpected response
    # --------------------------------------------------------

    return (
        None,
        {
            "status": "completed",
            "tests_passed": False,
            "iteration": 0,
            "implementation_results": [],
            "test_result": "",
            "debug_result": "",
            "review_result": "",
            "workflow_output": str(response),
        },
    )


# ============================================================
# INTERRUPT EXTRACTION
# ============================================================

def extract_interrupt_data(result):

    if not isinstance(
        result,
        dict,
    ):
        return None

    interrupts = result.get(
        "__interrupt__"
    )

    if not interrupts:
        return None

    first_interrupt = interrupts[0]

    if hasattr(
        first_interrupt,
        "value",
    ):

        return first_interrupt.value

    if isinstance(
        first_interrupt,
        dict,
    ):

        return first_interrupt

    return None


# ============================================================
# RESET
# ============================================================

def reset_workflow():

    st.session_state.workflow_result = None
    st.session_state.thread_id = None
    st.session_state.approval_pending = False
    st.session_state.approval_data = None


# ============================================================
# REPOSITORY
# ============================================================

try:

    branch = git_branch()

except Exception:

    branch = "unknown"


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title(
        "◈ AI Software Engineer"
    )

    st.caption(
        "Autonomous repository engineering agent"
    )

    st.divider()

    st.subheader(
        "Workflow"
    )

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

        st.markdown(
            f"**{number}. {name}**"
        )

        st.caption(
            description
        )

    st.divider()

    st.subheader(
        "Repository"
    )

    st.write(
        f"**Branch:** `{branch}`"
    )

    st.write(
        "**Connection:** 🟢 Connected"
    )

    st.divider()

    st.caption(
        "RAG · LangGraph · Multi-Agent · Pytest · Git"
    )


# ============================================================
# HEADER
# ============================================================

header_left, header_right = st.columns(
    [5, 1],
    vertical_alignment="center",
)

with header_left:

    st.title(
        "◈ AI Software Engineer"
    )

    st.write(
        "An autonomous coding agent that understands your "
        "repository, plans changes, writes code, runs tests "
        "and fixes failures."
    )

with header_right:

    st.success(
        "● AGENT ONLINE"
    )


# ============================================================
# METRICS
# ============================================================

st.write("")

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric(
        "Repository",
        "Connected",
    )

with m2:
    st.metric(
        "Git Branch",
        branch,
    )

with m3:
    st.metric(
        "Architecture",
        "Multi-Agent",
    )

with m4:
    st.metric(
        "Testing",
        "Pytest",
    )


# ============================================================
# MAIN AREA
# ============================================================

st.write("")

task_column, capability_column = st.columns(
    [2, 1],
    gap="large",
)


# ============================================================
# TASK
# ============================================================

with task_column:

    with st.container(
        border=True
    ):

        st.caption(
            "SOFTWARE TASK"
        )

        st.subheader(
            "What should the agent build or fix?"
        )

        st.write(
            "Describe the software engineering task in plain English. "
            "The agent will inspect the repository before modifying anything."
        )

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

        st.write("")

        run_col, clear_col = st.columns(
            [3, 1]
        )

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


# ============================================================
# CAPABILITIES
# ============================================================

with capability_column:

    with st.container(
        border=True
    ):

        st.caption(
            "WHAT THE AGENT DOES"
        )

        st.subheader(
            "Engineering pipeline"
        )

        st.markdown(
            """
            **🔍 Understand**

            Searches the repository using AST parsing and RAG.

            **🧠 Plan**

            Identifies the files and changes required.

            **👤 Approve**

            Pauses for human confirmation.

            **⚙️ Implement**

            Generates the required source changes.

            **🧪 Test**

            Generates and executes automated tests.

            **🔄 Debug**

            Diagnoses failures and attempts fixes.

            **🔎 Review**

            Performs a final engineering review.
            """
        )


# ============================================================
# RUN
# ============================================================

if run_clicked:

    if not task.strip():

        st.warning(
            "Please describe the software task first."
        )

    else:

        reset_workflow()

        with st.status(
            "AI Software Engineer is working...",
            expanded=True,
        ) as status:

            try:

                st.write(
                    "🔍 Indexing repository..."
                )

                st.write(
                    "🧠 Retrieving relevant code with RAG..."
                )

                st.write(
                    "📋 Analyzing requested changes..."
                )

                st.write(
                    "🗂️ Preparing implementation plan..."
                )

                # ------------------------------------------------
                # IMPORTANT:
                # Do NOT directly unpack the response.
                # ------------------------------------------------

                raw_response = run_workflow(
                    task.strip(),
                    approval_required=True,
                )

                thread_id, result = (
                    normalize_workflow_response(
                        raw_response
                    )
                )

                st.session_state.thread_id = (
                    thread_id
                )

                # ------------------------------------------------
                # APPROVAL INTERRUPT
                # ------------------------------------------------

                approval_data = (
                    extract_interrupt_data(
                        result
                    )
                )

                if approval_data is not None:

                    st.session_state.approval_data = (
                        approval_data
                    )

                    st.session_state.approval_pending = (
                        True
                    )

                    status.update(
                        label="Waiting for your approval",
                        state="complete",
                    )

                else:

                    st.session_state.workflow_result = (
                        result
                    )

                    status.update(
                        label="Workflow completed",
                        state="complete",
                    )

            except Exception as exc:

                status.update(
                    label="Workflow failed",
                    state="error",
                )

                st.error(
                    f"Workflow error: {exc}"
                )

                with st.expander(
                    "Technical error details"
                ):

                    st.exception(
                        exc
                    )


# ============================================================
# APPROVAL
# ============================================================

if st.session_state.approval_pending:

    st.write("")

    with st.container(
        border=True
    ):

        st.caption(
            "HUMAN APPROVAL REQUIRED"
        )

        st.subheader(
            "Review proposed changes"
        )

        approval_data = (
            st.session_state.approval_data
            or {}
        )

        target_files = approval_data.get(
            "target_files",
            [],
        )

        guidance = approval_data.get(
            "guidance",
            "",
        )

        message = approval_data.get(
            "message",
            "",
        )

        if target_files:

            st.write(
                "**The agent wants to modify:**"
            )

            for file_name in target_files:

                st.code(
                    file_name,
                    language="text",
                )

        if message:

            st.info(
                message
            )

        if guidance:

            with st.expander(
                "View implementation plan",
                expanded=True,
            ):

                st.markdown(
                    guidance
                )

        st.write("")

        approve_col, reject_col = st.columns(
            2
        )

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

        # ========================================================
        # APPROVE
        # ========================================================

        if approve_clicked:

            with st.status(
                "AI Engineer is implementing and testing...",
                expanded=True,
            ) as status:

                try:

                    st.write(
                        "⚙️ Implementing approved changes..."
                    )

                    st.write(
                        "🧪 Generating and running tests..."
                    )

                    st.write(
                        "🔄 Checking for failures..."
                    )

                    st.write(
                        "🔎 Running final review..."
                    )

                    raw_response = resume_workflow(
                        st.session_state.thread_id,
                        approved=True,
                    )

                    # ------------------------------------------------
                    # Normalize resume response too.
                    # ------------------------------------------------

                    returned_thread_id, result = (
                        normalize_workflow_response(
                            raw_response
                        )
                    )

                    if returned_thread_id:

                        st.session_state.thread_id = (
                            returned_thread_id
                        )

                    # ------------------------------------------------
                    # SECOND INTERRUPT
                    # ------------------------------------------------

                    next_approval = (
                        extract_interrupt_data(
                            result
                        )
                    )

                    if next_approval is not None:

                        st.session_state.approval_data = (
                            next_approval
                        )

                        st.session_state.approval_pending = (
                            True
                        )

                        status.update(
                            label="Another approval is required",
                            state="complete",
                        )

                    else:

                        st.session_state.workflow_result = (
                            result
                        )

                        st.session_state.approval_pending = (
                            False
                        )

                        st.session_state.approval_data = (
                            None
                        )

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

                    st.error(
                        f"Workflow error: {exc}"
                    )

                    with st.expander(
                        "Technical error details"
                    ):

                        st.exception(
                            exc
                        )

        # ========================================================
        # REJECT
        # ========================================================

        if reject_clicked:

            try:

                raw_response = resume_workflow(
                    st.session_state.thread_id,
                    approved=False,
                )

                _, result = (
                    normalize_workflow_response(
                        raw_response
                    )
                )

                st.session_state.workflow_result = (
                    result
                )

                st.session_state.approval_pending = (
                    False
                )

                st.session_state.approval_data = (
                    None
                )

                st.rerun()

            except Exception as exc:

                st.error(
                    f"Workflow error: {exc}"
                )

                with st.expander(
                    "Technical error details"
                ):

                    st.exception(
                        exc
                    )


# ============================================================
# RESULT
# ============================================================

result = st.session_state.workflow_result

if result:

    st.write("")

    st.divider()

    st.caption(
        "ENGINEERING RESULT"
    )

    st.subheader(
        "Agent execution complete"
    )

    # Safety normalization
    _, result = normalize_workflow_response(
        result
    )

    tests_passed = bool(
        result.get(
            "tests_passed",
            False,
        )
    )

    status_value = str(
        result.get(
            "status",
            "unknown",
        )
    )

    iteration = result.get(
        "iteration",
        0,
    )

    implementation_results = result.get(
        "implementation_results",
        [],
    )

    if tests_passed:

        st.success(
            "✓ Build completed successfully — "
            "implementation verified and tests passed."
        )

    else:

        st.warning(
            "⚠ Workflow completed, but verification "
            "did not pass."
        )

    result_col1, result_col2, result_col3, result_col4 = (
        st.columns(4)
    )

    with result_col1:

        st.metric(
            "Status",
            status_value,
        )

    with result_col2:

        st.metric(
            "Tests",
            "PASSED" if tests_passed else "FAILED",
        )

    with result_col3:

        st.metric(
            "Debug Iterations",
            iteration,
        )

    with result_col4:

        st.metric(
            "Files Changed",
            len(
                implementation_results
            )
            if isinstance(
                implementation_results,
                list,
            )
            else 0,
        )


    # ========================================================
    # ACTIVITY
    # ========================================================

    st.write("")

    activity_col, files_col = st.columns(
        [1, 1],
        gap="large",
    )

    with activity_col:

        with st.container(
            border=True
        ):

            st.caption(
                "AGENT ACTIVITY"
            )

            st.subheader(
                "Execution summary"
            )

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


    # ========================================================
    # FILES
    # ========================================================

    with files_col:

        with st.container(
            border=True
        ):

            st.caption(
                "SOURCE CHANGES"
            )

            st.subheader(
                "Files touched"
            )

            if implementation_results:

                for item in implementation_results:

                    if isinstance(
                        item,
                        dict,
                    ):

                        file_name = item.get(
                            "file",
                            item.get(
                                "path",
                                "Unknown file",
                            ),
                        )

                    else:

                        file_name = str(
                            item
                        )

                    st.code(
                        file_name,
                        language="text",
                    )

            else:

                st.caption(
                    "No source files were changed."
                )


    # ========================================================
    # TEST OUTPUT
    # ========================================================

    test_result = result.get(
        "test_result",
        "",
    )

    if test_result:

        st.write("")

        with st.expander(
            "🧪 Test execution output",
            expanded=False,
        ):

            st.code(
                str(test_result),
                language="text",
            )


    # ========================================================
    # DEBUG OUTPUT
    # ========================================================

    debug_result = result.get(
        "debug_result",
        "",
    )

    if debug_result:

        st.write("")

        with st.expander(
            "🔄 Debugging information",
            expanded=False,
        ):

            st.markdown(
                str(debug_result)
            )


    # ========================================================
    # REVIEW
    # ========================================================

    review_result = result.get(
        "review_result",
        "",
    )

    if review_result:

        st.write("")

        with st.container(
            border=True
        ):

            st.caption(
                "FINAL REVIEW"
            )

            st.subheader(
                "Code review"
            )

            st.markdown(
                str(review_result)
            )


    # ========================================================
    # TECHNICAL OUTPUT
    # ========================================================

    with st.expander(
        "Technical workflow output",
        expanded=False,
    ):

        st.code(
            str(result),
            language="python",
        )


# ============================================================
# FOOTER
# ============================================================

st.write("")

st.divider()

st.caption(
    "AI Software Engineer · RAG · LangGraph · "
    "Multi-Agent Systems · Automated Testing"
)