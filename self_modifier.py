"""
安全自修改模块 — 让 agent 能安全地修改自己的代码

安全流程：
  1. git commit 当前状态（保护点）
  2. 生成修改内容
  3. 写入文件
  4. 运行验证（import 测试 + 基本功能测试）
  5. 验证通过 → git commit 修改
  6. 验证失败 → git reset --hard 回滚到保护点

使用方式：
  from self_modifier import safe_modify
  result = safe_modify("agent.py", old_code, new_code, "修复了 XXX 问题")
"""

import os
import subprocess
import time
import re
import ast
from typing import Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 不允许修改的文件（核心安全边界）
PROTECTED_FILES = {
    "self_modifier.py",  # 不能改自己
    "config.py",         # 不能改配置（防止改 API key）
    ".env",              # 不能改环境变量
}

# 不允许的修改模式（安全红线）
FORBIDDEN_PATTERNS = [
    r"rm\s+-rf",           # 危险的删除命令
    r"os\.system\(",       # 系统命令注入
    r"subprocess\.call\(.*/bin/sh",  # shell 注入
    r"__import__\s*\(\s*['\"]subprocess",  # 动态导入 subprocess
    r"eval\s*\(",          # eval 注入
    r"exec\s*\(",          # exec 注入（注意：有些场景是合法的，需要人工判断）
]


def _git_exec(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """执行 git 命令"""
    return subprocess.run(
        ["git"] + args,
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=check,
        encoding="utf-8",
        errors="replace",
    )


def git_protect(label: str = "auto-save") -> str:
    """
    创建保护点：git add + commit。
    返回 commit hash，用于回滚。
    """
    _git_exec(["add", "-A"])
    result = _git_exec(["commit", "-m", f"[REM-protect] {label}", "--allow-empty"], check=False)
    # 获取当前 commit hash
    hash_result = _git_exec(["rev-parse", "HEAD"])
    return hash_result.stdout.strip()


def git_rollback(commit_hash: str) -> bool:
    """回滚到指定 commit"""
    try:
        _git_exec(["reset", "--hard", commit_hash])
        return True
    except subprocess.CalledProcessError:
        return False


def git_commit_changes(message: str) -> bool:
    """提交当前修改"""
    try:
        _git_exec(["add", "-A"])
        _git_exec(["commit", "-m", f"[REM-modify] {message}"])
        return True
    except subprocess.CalledProcessError:
        return False


def _check_file_allowed(file_path: str) -> tuple[bool, str]:
    """检查文件是否允许修改"""
    filename = os.path.basename(file_path)
    if filename in PROTECTED_FILES:
        return False, f"文件 {filename} 在保护列表中，不允许修改"
    return True, ""


def _check_content_safe(content: str) -> tuple[bool, str]:
    """检查内容是否包含危险模式"""
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, content):
            return False, f"内容包含危险模式: {pattern}"
    return True, ""


def _validate_python_syntax(file_path: str) -> tuple[bool, str]:
    """验证 Python 文件语法"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast.parse(source)
        return True, ""
    except SyntaxError as e:
        return False, f"语法错误: {e}"


def _validate_imports(file_path: str) -> tuple[bool, str]:
    """验证文件能被正常 import"""
    filename = os.path.basename(file_path)
    if not filename.endswith(".py"):
        return True, ""

    module_name = filename[:-3]
    # 跳过一些不方便 import 的模块
    skip_modules = {"main", "config"}
    if module_name in skip_modules:
        return True, ""

    try:
        import importlib
        # 尝试重新加载模块
        if module_name in __import__("sys").modules:
            importlib.reload(__import__("sys").modules[module_name])
        return True, ""
    except Exception as e:
        return False, f"Import 失败: {e}"


def _run_basic_tests() -> tuple[bool, str]:
    """运行基本验证测试"""
    tests = [
        # 测试核心模块能正常 import
        ("from tools.registry import ToolRegistry", "ToolRegistry"),
        ("from skill_engine import SkillEngine", "SkillEngine"),
        ("from persona_manager import PersonaManager", "PersonaManager"),
        ("from workflow_state import WorkflowState", "WorkflowState"),
    ]

    failures = []
    for code, name in tests:
        try:
            exec(code)
        except Exception as e:
            failures.append(f"{name}: {e}")

    if failures:
        return False, "基本测试失败:\n" + "\n".join(failures)
    return True, ""


def safe_modify(
    file_path: str,
    old_content: str,
    new_content: str,
    reason: str,
    skip_tests: bool = False,
) -> dict:
    """
    安全修改文件。

    参数：
      file_path: 相对于 BASE_DIR 的文件路径
      old_content: 要替换的旧内容（空字符串 = 新建文件）
      new_content: 新内容
      reason: 修改原因（会写入 commit message）
      skip_tests: 是否跳过测试（仅用于非关键文件）

    返回：
      {"success": bool, "message": str, "commit": str, "rolled_back": bool}
    """
    abs_path = os.path.join(BASE_DIR, file_path)

    # 1. 安全检查
    allowed, msg = _check_file_allowed(file_path)
    if not allowed:
        return {"success": False, "message": msg, "rolled_back": False}

    safe, msg = _check_content_safe(new_content)
    if not safe:
        return {"success": False, "message": msg, "rolled_back": False}

    # 2. 创建保护点
    protect_hash = git_protect(f"before modifying {file_path}: {reason}")

    # 3. 应用修改
    if old_content:
        # 替换模式
        if not os.path.isfile(abs_path):
            return {"success": False, "message": f"文件不存在: {file_path}", "rolled_back": False}
        with open(abs_path, "r", encoding="utf-8") as f:
            current = f.read()
        if old_content not in current:
            return {"success": False, "message": "找不到要替换的内容", "rolled_back": False}
        new_file_content = current.replace(old_content, new_content, 1)
    else:
        # 新建模式
        new_file_content = new_content

    # 写入文件
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(new_file_content)

    # 4. 验证
    if file_path.endswith(".py"):
        # 语法检查
        ok, msg = _validate_python_syntax(abs_path)
        if not ok:
            git_rollback(protect_hash)
            return {"success": False, "message": f"语法验证失败，已回滚: {msg}", "rolled_back": True}

    if not skip_tests:
        # Import 检查
        ok, msg = _validate_imports(abs_path)
        if not ok:
            git_rollback(protect_hash)
            return {"success": False, "message": f"Import 验证失败，已回滚: {msg}", "rolled_back": True}

        # 基本功能测试
        ok, msg = _run_basic_tests()
        if not ok:
            git_rollback(protect_hash)
            return {"success": False, "message": f"基本测试失败，已回滚: {msg}", "rolled_back": True}

    # 5. 提交修改
    git_commit_changes(f"modify {file_path}: {reason}")

    return {
        "success": True,
        "message": f"修改成功: {file_path}",
        "commit": protect_hash,
        "rolled_back": False,
    }


def safe_create(file_path: str, content: str, reason: str) -> dict:
    """安全创建新文件"""
    return safe_modify(file_path, "", content, reason)


def get_git_log(limit: int = 10) -> list[dict]:
    """获取最近的 git 日志"""
    try:
        result = _git_exec(["log", f"--oneline", f"-{limit}"])
        lines = result.stdout.strip().split("\n")
        return [{"hash": line[:7], "message": line[8:]} for line in lines if line]
    except Exception:
        return []


def rollback_to(commit_hash: str) -> dict:
    """手动回滚到指定 commit"""
    ok = git_rollback(commit_hash)
    if ok:
        return {"success": True, "message": f"已回滚到 {commit_hash}"}
    return {"success": False, "message": f"回滚失败"}


class SelfModifier:
    """
    安全自修改流程的状态机。

    用法：
      mod = SelfModifier("优化 memory_store 搜索算法")
      mod.start()                    # 创建保护分支
      mod.verify("memory_store.py")  # 验证修改
      mod.commit("优化搜索算法")      # 提交并合并
      # 或 mod.rollback("验证失败")   # 回滚
    """

    def __init__(self, description: str):
        self.description = description
        self.started = False
        self.branch_name = ""
        self.original_branch = ""
        self.protect_hash = ""
        self.modified_files: list[str] = []

    def start(self) -> dict:
        """启动修改流程：创建保护点"""
        if self.started:
            return {"success": False, "message": "已有进行中的修改流程"}

        try:
            # 记录当前分支
            result = _git_exec(["branch", "--show-current"])
            self.original_branch = result.stdout.strip() or "master"

            # 创建保护点
            self.protect_hash = git_protect(f"self-mod start: {self.description}")

            # 创建安全分支
            ts = int(time.time())
            self.branch_name = f"self-mod/{ts}"
            _git_exec(["checkout", "-b", self.branch_name])

            self.started = True
            return {
                "success": True,
                "message": f"已创建安全分支 {self.branch_name}",
                "branch": self.branch_name,
                "protect_hash": self.protect_hash,
            }
        except Exception as e:
            return {"success": False, "message": f"启动失败: {e}"}

    def verify(self, file_path: str) -> dict:
        """验证修改后的文件"""
        if not self.started:
            return {"success": False, "message": "没有进行中的修改流程"}

        abs_path = os.path.join(BASE_DIR, file_path)
        if not os.path.isfile(abs_path):
            return {"success": False, "message": f"文件不存在: {file_path}"}

        checks = []

        # Python 语法检查
        if file_path.endswith(".py"):
            ok, msg = _validate_python_syntax(abs_path)
            checks.append({"check": "syntax", "passed": ok, "detail": msg})

        # Import 检查
        ok, msg = _validate_imports(abs_path)
        checks.append({"check": "import", "passed": ok, "detail": msg})

        # 基本功能测试
        ok, msg = _run_basic_tests()
        checks.append({"check": "basic_tests", "passed": ok, "detail": msg})

        all_passed = all(c["passed"] for c in checks)

        if file_path not in self.modified_files:
            self.modified_files.append(file_path)

        return {
            "success": all_passed,
            "checks": checks,
            "message": "验证通过" if all_passed else "验证失败",
        }

    def commit(self, message: str) -> dict:
        """提交修改并合并回原分支"""
        if not self.started:
            return {"success": False, "message": "没有进行中的修改流程"}

        try:
            # 提交
            ok = git_commit_changes(message)
            if not ok:
                return {"success": False, "message": "提交失败，可能没有修改"}

            # 切回原分支并合并
            _git_exec(["checkout", self.original_branch])
            _git_exec(["merge", self.branch_name, "--no-ff", "-m", f"[REM-self-mod] {message}"])

            # 删除安全分支
            _git_exec(["branch", "-D", self.branch_name], check=False)

            self.started = False
            return {
                "success": True,
                "message": f"已提交并合并到 {self.original_branch}",
                "branch": self.original_branch,
                "modified_files": self.modified_files,
            }
        except Exception as e:
            # 合并失败，尝试回滚
            self.rollback(f"合并失败: {e}")
            return {"success": False, "message": f"合并失败，已回滚: {e}"}

    def rollback(self, reason: str = "") -> dict:
        """回滚所有修改"""
        if not self.started:
            return {"success": False, "message": "没有进行中的修改流程"}

        try:
            # 切回原分支
            _git_exec(["checkout", self.original_branch], check=False)

            # 回滚到保护点
            if self.protect_hash:
                git_rollback(self.protect_hash)

            # 删除安全分支
            _git_exec(["branch", "-D", self.branch_name], check=False)

            self.started = False
            return {
                "success": True,
                "message": f"已回滚到 {self.protect_hash[:7]}",
                "reason": reason,
            }
        except Exception as e:
            return {"success": False, "message": f"回滚异常: {e}"}
