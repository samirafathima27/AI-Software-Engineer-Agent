from app.graph.workflow import (
    run_interactive_workflow,
)


def main():

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
        "\nPowered by:"
    )

    print(
        "  • RAG"
    )

    print(
        "  • Multi-Agent Architecture"
    )

    print(
        "  • LangGraph"
    )

    print(
        "  • Automated Testing"
    )

    print(
        "  • Debugging Loop"
    )

    print(
        "  • Human Approval"
    )

    print(
        "  • Persistent State"
    )

    print(
        "\nType 'exit' to quit."
    )

    while True:

        print(
            "\n----------------------------------------"
        )

        task = input(
            "\nYou: "
        ).strip()

        if task.lower() == "exit":

            print(
                "\nGoodbye."
            )

            break

        if not task:

            continue

        try:

            run_interactive_workflow(
                task
            )

        except KeyboardInterrupt:

            print(
                "\n\nWorkflow interrupted."
            )

        except Exception as e:

            print(
                "\nWorkflow error:"
            )

            print(
                e
            )


if __name__ == "__main__":

    main()