from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _validate_repository() -> Path:
    """
    Ensure the AI Software Engineer Agent project
    is a Git repository.
    """

    git_dir = PROJECT_ROOT / ".git"

    if not git_dir.exists():
        raise RuntimeError(
            f"Project is not a Git repository: {PROJECT_ROOT}"
        )

    return PROJECT_ROOT


def _run_git(
    *args: str,
    cwd: Path | None = None,
) -> str:
    """
    Run a controlled Git command.
    """

    repository = cwd or _validate_repository()

    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Git command failed:\n"
            f"git {' '.join(args)}\n\n"
            f"{result.stderr.strip()}"
        )

    return result.stdout.strip()


def git_status() -> str:
    """
    Return current Git working-tree status.
    """

    return _run_git(
        "status",
        "--short",
        "--branch",
    )


def git_diff(
    staged: bool = False,
) -> str:
    """
    Return current Git diff.

    staged=False:
        Show unstaged changes.

    staged=True:
        Show staged changes.
    """

    if staged:
        return _run_git(
            "diff",
            "--cached",
        )

    return _run_git(
        "diff",
    )


def git_branch() -> str:
    """
    Return the current branch name.
    """

    return _run_git(
        "branch",
        "--show-current",
    )


def git_create_branch(
    branch_name: str,
) -> str:
    """
    Create and switch to a new Git branch.
    """

    branch_name = branch_name.strip()

    if not branch_name:
        raise ValueError(
            "Branch name cannot be empty."
        )

    unsafe_characters = [
        " ",
        "..",
        "~",
        "^",
        ":",
        "?",
        "*",
        "[",
        "\\",
    ]

    if any(
        character in branch_name
        for character in unsafe_characters
    ):
        raise ValueError(
            f"Unsafe Git branch name: {branch_name}"
        )

    return _run_git(
        "switch",
        "-c",
        branch_name,
    )


def git_stage_all() -> str:
    """
    Stage all repository changes.
    """

    return _run_git(
        "add",
        "-A",
    )


def git_commit(
    message: str,
) -> str:
    """
    Create a Git commit.
    """

    message = message.strip()

    if not message:
        raise ValueError(
            "Commit message cannot be empty."
        )

    return _run_git(
        "commit",
        "-m",
        message,
    )


def git_log(
    limit: int = 5,
) -> str:
    """
    Return recent Git commits.
    """

    if limit < 1:
        raise ValueError(
            "Log limit must be at least 1."
        )

    limit = min(limit, 50)

    return _run_git(
        "log",
        f"-{limit}",
        "--oneline",
        "--decorate",
    )


def git_has_changes() -> bool:
    """
    Return True when the repository has
    staged or unstaged changes.
    """

    status = git_status()

    lines = status.splitlines()

    return any(
        line.strip()
        and not line.startswith("##")
        for line in lines
    )