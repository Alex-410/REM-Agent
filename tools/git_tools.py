import subprocess
import os


def _git_cmd(*args: str, timeout: int = 15) -> dict:
    """Run a git command and return the result."""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=timeout,
            cwd=os.getcwd(),
        )
        return {
            "stdout": result.stdout.strip()[-3000:] if result.stdout else "",
            "stderr": result.stderr.strip()[-2000:] if result.stderr else "",
            "return_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Git command timed out"}
    except FileNotFoundError:
        return {"error": "Git not found. Is git installed?"}
    except Exception as e:
        return {"error": str(e)}


def git_status() -> dict:
    """Show the working tree status (modified, staged, untracked files)."""
    return _git_cmd("status", "--short")


def git_diff(staged: bool = False, path: str = "") -> dict:
    """Show changes in the working tree."""
    args = ["diff"]
    if staged:
        args.append("--staged")
    if path:
        args.append("--", path)
    return _git_cmd(*args)


def git_log(max_count: int = 10, branch: str = "") -> dict:
    """Show recent commit history."""
    args = ["log", f"--max-count={max_count}", "--oneline", "--graph"]
    if branch:
        args.append(branch)
    return _git_cmd(*args)


def git_commit(message: str) -> dict:
    """Create a new git commit with the given message."""
    result = _git_cmd("commit", "-m", message)
    return result


def git_branch(list_all: bool = False) -> dict:
    """List git branches."""
    args = ["branch"]
    if list_all:
        args.append("-a")
    return _git_cmd(*args)


def git_show(commit: str = "HEAD") -> dict:
    """Show the details of a specific commit."""
    return _git_cmd("show", commit, "--stat", "--no-patch")
