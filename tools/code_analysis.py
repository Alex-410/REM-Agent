import os
import glob


def code_search(pattern: str, path: str = ".", max_results: int = 20) -> dict:
    """Search for text patterns in code files using Python's built-in search.

    Use this to find function definitions, variable references, imports, etc.
    """
    full_path = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)

    # File extensions to search
    extensions = {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".scss",
        ".json", ".yaml", ".yml", ".md", ".sh", ".bat", ".toml", ".cfg",
        ".ini", ".env", ".txt", ".vue", ".svelte", ".java", ".go", ".rs",
        ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".kt",
    }

    results = []
    searched_files = 0

    try:
        for root, dirs, files in os.walk(full_path):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in (
                "node_modules", ".git", "__pycache__", ".venv", "venv",
                "dist", "build", ".next", ".claude"
            )]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in extensions:
                    continue

                filepath = os.path.join(root, file)
                if not os.path.isfile(filepath):
                    continue

                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, 1):
                            if pattern in line:
                                rel_path = os.path.relpath(filepath, os.getcwd())
                                results.append({
                                    "file": rel_path.replace("\\", "/"),
                                    "line": line_no,
                                    "content": line.strip()[:200],
                                })
                                if len(results) >= max_results:
                                    return {
                                        "pattern": pattern,
                                        "results": results,
                                        "total_matches": len(results),
                                        "files_searched": searched_files,
                                        "truncated": True,
                                    }
                    searched_files += 1
                except (OSError, UnicodeDecodeError):
                    continue

    except Exception as e:
        return {"error": str(e)}

    return {
        "pattern": pattern,
        "results": results,
        "total_matches": len(results),
        "files_searched": searched_files,
        "truncated": False,
    }


def project_structure(path: str = ".", max_depth: int = 3) -> dict:
    """Analyze project structure and return an overview."""
    full_path = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)

    exclude_dirs = {
        "node_modules", ".git", "__pycache__", ".venv", "venv", "dist",
        "build", ".next", ".claude", ".vite", ".cache",
    }
    exclude_files = {".DS_Store", "Thumbs.db", "*.pyc"}

    structure = []
    file_counts = {}
    total_size = 0
    total_files = 0

    try:
        root_path = full_path.rstrip(os.sep)
        for current_root, dirs, files in os.walk(root_path):
            # Skip excluded dirs
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            rel_root = os.path.relpath(current_root, root_path)
            depth = rel_root.count(os.sep) + 1 if rel_root != "." else 0

            if depth > max_depth:
                dirs.clear()
                continue

            for f in files:
                if f in exclude_files:
                    continue
                filepath = os.path.join(current_root, f)
                file_ext = os.path.splitext(f)[1] or "(no ext)"
                file_counts[file_ext] = file_counts.get(file_ext, 0) + 1
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass
                total_files += 1

            if depth <= max_depth:
                indent = "  " * depth
                dir_name = os.path.basename(current_root) or os.path.basename(os.path.dirname(current_root))
                structure.append(f"{indent}{dir_name}/")
                for f in sorted(files):
                    if f not in exclude_files:
                        structure.append(f"{indent}  {f}")

    except Exception as e:
        return {"error": str(e)}

    # Summarize
    top_extensions = sorted(file_counts.items(), key=lambda x: -x[1])[:10]

    return {
        "root": os.path.basename(root_path),
        "total_files": total_files,
        "total_size_bytes": total_size,
        "tree": "\n".join(structure[:100]),
        "top_extensions": [{"ext": ext, "count": count} for ext, count in top_extensions],
        "tree_truncated": len(structure) > 100,
    }
