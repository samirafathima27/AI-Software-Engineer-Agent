from pathlib import Path
from uuid import uuid4

from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from langgraph.types import Command

from langgraph.checkpoint.sqlite import (
    SqliteSaver,
)

from app.graph.state import AgentState

from app.graph.nodes import (
    initialize_node,
    index_node,
    retrieve_node,
    analyze_node,
    plan_node,
    approval_node,
    implement_node,
    refresh_index_node,
    test_node,
    run_tests_node,
    debug_node,
    review_node,
    finalize_node,
    route_after_approval,
    route_after_tests,
    route_after_debug,
)


CHECKPOINT_DIRECTORY = Path(
    "data/langgraph"
)

CHECKPOINT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

CHECKPOINT_DATABASE = (
    CHECKPOINT_DIRECTORY
    / "checkpoints.sqlite"
)

GRAPH_DIRECTORY = Path(
    "logs"
)

GRAPH_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

GRAPH_MERMAID_FILE = (
    GRAPH_DIRECTORY
    / "agent_workflow.mmd"
)


# ============================================================
# BUILD GRAPH
# ============================================================

def build_workflow(
    checkpointer
):

    graph = StateGraph(
        AgentState
    )

    # --------------------------------------------------------
    # NODES
    # --------------------------------------------------------

    graph.add_node(
        "initialize",
        initialize_node,
    )

    graph.add_node(
        "index",
        index_node,
    )

    graph.add_node(
        "retrieve",
        retrieve_node,
    )

    graph.add_node(
        "analyze",
        analyze_node,
    )

    graph.add_node(
        "plan",
        plan_node,
    )

    graph.add_node(
        "approval",
        approval_node,
    )

    graph.add_node(
        "implement",
        implement_node,
    )

    graph.add_node(
        "refresh_index",
        refresh_index_node,
    )

    graph.add_node(
        "test",
        test_node,
    )

    graph.add_node(
        "run_tests",
        run_tests_node,
    )

    graph.add_node(
        "debug",
        debug_node,
    )

    graph.add_node(
        "review",
        review_node,
    )

    graph.add_node(
        "finalize",
        finalize_node,
    )

    # --------------------------------------------------------
    # MAIN FLOW
    # --------------------------------------------------------

    graph.add_edge(
        START,
        "initialize",
    )

    graph.add_edge(
        "initialize",
        "index",
    )

    graph.add_edge(
        "index",
        "retrieve",
    )

    graph.add_edge(
        "retrieve",
        "analyze",
    )

    graph.add_edge(
        "analyze",
        "plan",
    )

    graph.add_edge(
        "plan",
        "approval",
    )

    # --------------------------------------------------------
    # HUMAN APPROVAL ROUTING
    # --------------------------------------------------------

    graph.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "implement": "implement",
            "finalize": "finalize",
        },
    )

    # --------------------------------------------------------
    # IMPLEMENTATION
    # --------------------------------------------------------

    graph.add_edge(
        "implement",
        "refresh_index",
    )

    graph.add_edge(
        "refresh_index",
        "test",
    )

    graph.add_edge(
        "test",
        "run_tests",
    )

    # --------------------------------------------------------
    # TEST ROUTING
    # --------------------------------------------------------

    graph.add_conditional_edges(
        "run_tests",
        route_after_tests,
        {
            "review": "review",
            "debug": "debug",
        },
    )

    # --------------------------------------------------------
    # DEBUG LOOP
    # --------------------------------------------------------

    graph.add_conditional_edges(
        "debug",
        route_after_debug,
        {
            "refresh": "refresh_index",
            "review": "review",
        },
    )

    # --------------------------------------------------------
    # END
    # --------------------------------------------------------

    graph.add_edge(
        "review",
        END,
    )

    graph.add_edge(
        "finalize",
        END,
    )

    return graph.compile(
        checkpointer=checkpointer
    )


# ============================================================
# SAVE GRAPH VISUALIZATION
# ============================================================

def save_graph_visualization(
    workflow
) -> str:

    drawable_graph = workflow.get_graph()

    mermaid = drawable_graph.draw_mermaid()

    GRAPH_MERMAID_FILE.write_text(
        mermaid,
        encoding="utf-8"
    )

    return str(
        GRAPH_MERMAID_FILE
    )


# ============================================================
# THREAD ID
# ============================================================

def create_thread_id() -> str:

    return str(
        uuid4()
    )


# ============================================================
# RUN WORKFLOW
# ============================================================

def run_workflow(
    task: str,
    thread_id: str | None = None,
    approval_required: bool = True,
) -> dict:

    if thread_id is None:

        thread_id = create_thread_id()

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    with SqliteSaver.from_conn_string(
        str(CHECKPOINT_DATABASE)
    ) as checkpointer:

        workflow = build_workflow(
            checkpointer
        )

        save_graph_visualization(
            workflow
        )

        initial_state: AgentState = {
            "task": task,
            "iteration": 0,
            "max_iterations": 3,
            "approval_required": (
                approval_required
            ),
            "approval_granted": False,
            "status": "starting",
            "tests_passed": False,
        }

        result = workflow.invoke(
            initial_state,
            config
        )

        return {
            "thread_id": thread_id,
            "result": result,
        }


# ============================================================
# RESUME WORKFLOW
# ============================================================

def resume_workflow(
    thread_id: str,
    approved: bool,
) -> dict:

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    with SqliteSaver.from_conn_string(
        str(CHECKPOINT_DATABASE)
    ) as checkpointer:

        workflow = build_workflow(
            checkpointer
        )

        result = workflow.invoke(
            Command(
                resume={
                    "approved": approved
                }
            ),
            config
        )

        return {
            "thread_id": thread_id,
            "result": result,
        }


# ============================================================
# INTERACTIVE WORKFLOW
# ============================================================

def run_interactive_workflow(
    task: str
) -> dict:

    thread_id = create_thread_id()

    print(
        "\n========================================"
    )

    print(
        "       LANGGRAPH SOFTWARE AGENT"
    )

    print(
        "========================================"
    )

    print(
        f"\nThread ID: {thread_id}"
    )

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    with SqliteSaver.from_conn_string(
        str(CHECKPOINT_DATABASE)
    ) as checkpointer:

        workflow = build_workflow(
            checkpointer
        )

        graph_file = (
            save_graph_visualization(
                workflow
            )
        )

        print(
            f"\nGraph saved to: "
            f"{graph_file}"
        )

        initial_state: AgentState = {
            "task": task,
            "iteration": 0,
            "max_iterations": 3,
            "approval_required": True,
            "approval_granted": False,
            "status": "starting",
            "tests_passed": False,
        }

        result = workflow.invoke(
            initial_state,
            config
        )

        # ----------------------------------------------------
        # HUMAN APPROVAL
        # ----------------------------------------------------

        interrupts = result.get(
            "__interrupt__"
        )

        if interrupts:

            print(
                "\n========================================"
            )

            print(
                "       HUMAN APPROVAL REQUIRED"
            )

            print(
                "========================================"
            )

            interrupt_value = (
                interrupts[0].value
                if hasattr(
                    interrupts[0],
                    "value"
                )
                else interrupts[0]
            )

            if isinstance(
                interrupt_value,
                dict
            ):

                print(
                    "\nTask:"
                )

                print(
                    interrupt_value.get(
                        "task",
                        task
                    )
                )

                print(
                    "\nFiles that will be modified:"
                )

                for file_path in (
                    interrupt_value.get(
                        "target_files",
                        []
                    )
                ):

                    print(
                        f"  - {file_path}"
                    )

                print(
                    "\nGuidance:"
                )

                print(
                    interrupt_value.get(
                        "guidance",
                        ""
                    )
                )

            else:

                print(
                    interrupt_value
                )

            answer = input(
                "\nApprove changes? "
                "[y/N]: "
            ).strip().lower()

            approved = (
                answer
                in {
                    "y",
                    "yes"
                }
            )

            result = workflow.invoke(
                Command(
                    resume={
                        "approved": approved
                    }
                ),
                config
            )

        # ----------------------------------------------------
        # FINAL OUTPUT
        # ----------------------------------------------------

        print(
            "\n========================================"
        )

        print(
            "          WORKFLOW COMPLETE"
        )

        print(
            "========================================"
        )

        print(
            f"\nThread ID: "
            f"{thread_id}"
        )

        print(
            f"\nStatus: "
            f"{result.get('status')}"
        )

        print(
            f"\nTests passed: "
            f"{result.get('tests_passed')}"
        )

        print(
            f"\nDebug iterations: "
            f"{result.get('iteration', 0)}"
        )

        if result.get(
            "review_result"
        ):

            print(
                "\nREVIEW:"
            )

            print(
                result["review_result"]
            )

        return {
            "thread_id": thread_id,
            "result": result,
        }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "\n========================================"
    )

    print(
        "       LANGGRAPH SOFTWARE AGENT"
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

    run_interactive_workflow(
        task
    )