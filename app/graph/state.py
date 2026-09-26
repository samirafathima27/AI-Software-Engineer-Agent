from typing import TypedDict


class AgentState(TypedDict, total=False):

    # --------------------------------------------------------
    # USER REQUEST
    # --------------------------------------------------------

    task: str

    # --------------------------------------------------------
    # REPOSITORY
    # --------------------------------------------------------

    repository_context: str

    # --------------------------------------------------------
    # CODE AGENT
    # --------------------------------------------------------

    plan: str

    target_files: list[str]

    guidance: str

    # --------------------------------------------------------
    # IMPLEMENTATION
    # --------------------------------------------------------

    implementation_results: list[dict]

    # --------------------------------------------------------
    # TESTING
    # --------------------------------------------------------

    test_files: list[str]

    test_result: str

    tests_passed: bool

    # --------------------------------------------------------
    # DEBUGGING
    # --------------------------------------------------------

    debug_result: str

    debug_source_files: list[str]

    debug_test_files: list[str]

    debug_implementations: list[dict]

    # --------------------------------------------------------
    # REVIEW
    # --------------------------------------------------------

    review_result: str

    # --------------------------------------------------------
    # HUMAN APPROVAL
    # --------------------------------------------------------

    approval_required: bool

    approval_granted: bool

    approval_message: str

    # --------------------------------------------------------
    # WORKFLOW CONTROL
    # --------------------------------------------------------

    iteration: int

    max_iterations: int

    status: str

    error: str