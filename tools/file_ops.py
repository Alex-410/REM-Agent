import os
import glob


def read_file(path: str) -> dict:
    """Read the contents of a file."""
    try:
        full_path = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "path": path,
            "content": content[:10000],
            "size": len(content),
            "truncated": len(content) > 10000
        }
    except Exception as e:
        return {"error": str(e)}


def write_file(path: str, content: str) -> dict:
    """Write content to a file (creates or overwrites)."""
    try:
        full_path = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
        parent = os.path.dirname(full_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": path, "size": len(content)}
    except Exception as e:
        return {"error": str(e)}


def list_files(path: str = ".", pattern: str = "**/*") -> dict:
    """List files in a directory matching a pattern."""
    try:
        full_path = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
        files = glob.glob(os.path.join(full_path, pattern), recursive=True)
        files = [f.replace("\\", "/") for f in files]
        dirs = sorted(f for f in files if os.path.isdir(f))
        file_list = sorted(f for f in files if os.path.isfile(f))
        return {
            "path": path,
            "directories": dirs[:50],
            "files": file_list[:50],
            "total": len(files)
        }
    except Exception as e:
        return {"error": str(e)}
