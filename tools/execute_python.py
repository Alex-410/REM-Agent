import subprocess
import sys
import os


def execute_python(code: str) -> dict:
    """Execute Python code and return the result."""
    if len(code) > 10000:
        return {"error": "Code too long (max 10000 chars)"}
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=30,
            cwd=os.getcwd()
        )
        return {
            "stdout": result.stdout[-3000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "Execution timed out (30s)"}
    except Exception as e:
        return {"error": str(e)}
