import subprocess
import os

BLOCKED = ["rm -rf /", "mkfs", "dd if=", "> /dev/sda", ":(){ :|:& };:", "chmod 777 /"]


def bash(command: str) -> dict:
    """Execute a shell command."""
    for kw in BLOCKED:
        if kw in command.lower():
            return {"error": f"Command blocked: contains dangerous pattern"}
    try:
        result = subprocess.run(
            command, shell=True,
            capture_output=True, text=True, timeout=30,
            cwd=os.getcwd()
        )
        return {
            "stdout": result.stdout[-3000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "return_code": result.returncode,
            "error": result.stderr.strip() if result.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out (30s)"}
    except Exception as e:
        return {"error": str(e)}
