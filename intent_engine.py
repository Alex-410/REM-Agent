"""
意图引擎 — 模糊指令 → 理解 → 方案 → 执行 → 记住

工作流程：
  用户说"写个爱心代码"
     ↓
  1. 查记忆（memory_store）：以前做过类似的事吗？
     ├── 做过 → 加载记住的方案 → 直接执行
     └── 没做过 → 进入"学习模式"
               ↓
  2. 调用 LLM 理解意图，生成执行方案（JSON 步骤列表）
  3. 逐步骤执行（调用工具），每步反馈
  4. 执行完毕 → 方案+结果存到 memory_store
  5. 下次同样的指令 → 跳过 LLM，直接执行
"""

import json
import time
from typing import AsyncGenerator

import httpx
from openai import OpenAI

import config
import memory_store as mem
import output as output_mgr
import desktop_context
from tools.registry import ToolRegistry
from tools import register_all_tools
from llm_client import call_llm as _llm_call, call_llm_with_fallback

registry = ToolRegistry()
register_all_tools(registry)

# 待用户确认的记忆暂存池
_pending_memories: dict[str, dict] = {}

# 可用的工具简述（给 LLM 做方案时参考）
TOOL_SUMMARY = ""
_TOOL_SUMMARY_INIT = False

# 常用技能关键词（供 intent 引擎自查用）
COMMON_SKILL_DOMAINS = [
    "web scraping", "crawler", "data extraction",
    "image processing", "image generation", "draw",
    "api development", "api design",
    "database", "sql", "nosql",
    "devops", "docker", "deploy", "ci/cd",
    "nlp", "natural language", "text analysis",
    "time series", "data analysis", "visualization",
    "automation", "script", "workflow",
    "testing", "unit test", "e2e test",
    "security", "penetration", "auth",
    "chat", "messaging", "wechat", "telegram",
    "file operation", "pdf", "office",
]


def _get_tool_summary() -> str:
    global _TOOL_SUMMARY_INIT, TOOL_SUMMARY
    if not _TOOL_SUMMARY_INIT:
        lines = ["可用工具："]
        for d in registry.get_definitions():
            name = d["function"]["name"]
            desc = d["function"]["description"]
            params = list(d["function"]["parameters"].get("properties", {}).keys())
            param_str = ", ".join(params) if params else "(无参数)"
            lines.append(f"  - {name}({param_str}): {desc}")
        TOOL_SUMMARY = "\n".join(lines)
        _TOOL_SUMMARY_INIT = True
    return TOOL_SUMMARY


PLANNING_PROMPT = """你是一个能理解中文指令并拆解为可执行步骤的 AI 助手。

自学规则：
1. 遇到不知道的（具体命令、参数、API、操作步骤）→ 第一步先用 web_search 搜索
2. 搜索后把搜索结果中的关键信息用在后续步骤中
3. 不要编造不知道的命令或 API
4. 确保步骤完整覆盖从开始到最终目标

格式规则：
1. 输出严格 JSON 数组，每个元素一个步骤，格式：{{"step": 序号, "action": "工具名", "args": {{...}}, "description": "描述"}}
2. 步骤必须完整覆盖从开始到最终目标，不能停在中间步骤
3. 如果用户要求"发送"或"打包"，最终的步骤必须包含实际发送/打包的动作
4. 用 web_search 查不知道的信息，用 bash 执行命令，用 write_file 写文件
5. Windows 上打包用 python，不用 zip/tar 命令
6. 文件路径用绝对路径
7. 内容直接写完整内容，不要写占位符

可用工具：
{tools}

{output_rules}

示例：
用户：用微信给Rem发送你好
输出：[{{"step":1, "action":"wechat_send_text", "args":{{"contact":"Rem", "message":"你好"}}, "description":"给Rem发送文本消息"}}]

用户：写个爱心代码
输出：[{{"step":1, "action":"web_search", "args":{{"query":"python turtle heart code"}}, "description":"搜索爱心代码实现"}}, {{"step":2, "action":"write_file", "args":{{"path":"output/code/heart.py", "content":"..."}}, "description":"写入找到的代码"}}, {{"step":3, "action":"execute_python", "args":{{"code":"..."}}, "description":"运行查看效果"}}]

用户：给rem发送打包好的html代码
输出：[{{"step":1, "action":"list_files", "args":{{"path":"output/code", "pattern":"*.html"}}, "description":"看有没有html文件"}}, {{"step":2, "action":"bash", "args":{{"command":"python -c \"import shutil; shutil.make_archive(r'output/temp/code', 'zip', r'output/code')\""}}, "description":"打包"}}, {{"step":3, "action":"wechat_send_file", "args":{{"contact":"rem", "file_path":"output/temp/code.zip"}}, "description":"发送文件"}}]

注意：只输出 JSON 数组，不要加任何其他文字。如果用户指令包含"发送"或"打包"，最后一步必须是发送工具调用。"""


def _call_llm(system_prompt: str, user_message: str, temperature: float = 0.1) -> str | None:
    """调用 LLM 获取响应（带 fallback 降级）"""
    return _llm_call(system_prompt, user_message, temperature)


def _parse_plan(llm_output: str | None) -> list[dict] | None:
    """从 LLM 输出中解析出步骤列表"""
    if not llm_output:
        return None

    text = llm_output.strip()

    # 去掉可能的 ```json ... ``` 标记
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉第一行（```json）和最后一行（```）
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1])

    try:
        plan = json.loads(text)
        if isinstance(plan, list) and all(isinstance(s, dict) for s in plan):
            return plan
    except json.JSONDecodeError:
        pass

    # 尝试在文本中找 JSON 数组
    import re
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            plan = json.loads(match.group())
            if isinstance(plan, list) and all(isinstance(s, dict) for s in plan):
                return plan
        except json.JSONDecodeError:
            pass

    return None


async def execute_plan(
    plan: list[dict],
    max_retries: int = 2,
    user_input: str = "",
    plan_context: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """
    逐步骤执行方案，支持：
    - 步骤间上下文传递（上一步结果可被后续步骤引用）
    - 失败自动重试 + 自动修复
    - 彻底失败后用 LLM 重新规划剩余步骤
    """
    total = len(plan)
    step_context = plan_context or {}  # 累积步骤结果上下文
    remaining_plan = list(plan)

    i = 0
    while i < len(remaining_plan):
        step = remaining_plan[i]
        action = step.get("action", "")
        raw_args = step.get("args", {})
        desc = step.get("description", f"第 {i+1} 步")

        # === 变量替换：将 {step_N.result_key} 替换为实际值 ===
        args = _resolve_args(raw_args, step_context)

        last_error = None
        for attempt in range(max_retries + 1):
            if attempt > 0:
                yield {
                    "type": "step_retry",
                    "step": i + 1,
                    "total": total,
                    "action": action,
                    "attempt": attempt,
                    "max_retries": max_retries,
                    "last_error": str(last_error)[:300],
                }

            yield {
                "type": "step",
                "step": i + 1,
                "total": total,
                "action": action,
                "description": desc,
            }

            try:
                result = await registry.execute(action, args)
            except Exception as tool_err:
                result = {"error": str(tool_err)[:500]}

            error = isinstance(result, dict) and result.get("error")
            if not error:
                # 保存结果到上下文
                step_context[f"step_{i+1}"] = {
                    "action": action,
                    "args": args,
                    "result": result,
                }

                yield {
                    "type": "step_result",
                    "step": i + 1,
                    "action": action,
                    "result": result,
                }
                break  # success, next step

            last_error = error

            # Auto-fix: missing module → pip install
            if attempt == 0 and _can_auto_fix(error):
                fix_desc, fix_ok = await _auto_fix(error)
                yield {
                    "type": "auto_fix",
                    "step": i + 1,
                    "action": action,
                    "fix": fix_desc,
                    "success": fix_ok,
                }
                if fix_ok:
                    continue  # retry the step
        else:
            # === 彻底失败 → 用 LLM 重新规划后续步骤 ===
            yield {
                "type": "step_failed",
                "step": i + 1,
                "action": action,
                "error": str(last_error)[:500],
            }

            # 记录失败到技能缺口分析
            try:
                from skill_gap import record_failure
                record_failure(
                    user_input=user_input,
                    error=str(last_error)[:500],
                    failed_action=action,
                    context=desc,
                    source="intent",
                )
            except Exception:
                pass

            replan = await _replan_remaining_steps(
                user_input=user_input,
                failed_step=i + 1,
                failed_action=action,
                error=str(last_error)[:500],
                step_context=step_context,
                remaining_plan=remaining_plan[i + 1:],
            )

            if replan:
                yield {
                    "type": "replan",
                    "step": i + 1,
                    "original_action": action,
                    "new_plan": replan,
                }
                remaining_plan = remaining_plan[:i] + replan
                # 不前进 i，重新执行新规划的第一个步骤
                continue
            else:
                # 无法重新规划，跳过这个步骤继续
                step_context[f"step_{i+1}"] = {
                    "action": action,
                    "args": args,
                    "error": str(last_error)[:500],
                }

        i += 1

    yield {"type": "steps_done", "total": len(remaining_plan), "context": step_context}


def confirm_memory(pending_id: str, confirmed: bool = True) -> dict:
    """用户确认/拒绝后处理待保存的记忆"""
    data = _pending_memories.pop(pending_id, None)
    if not data:
        return {"success": False, "message": "确认超时或无效请求"}

    if not confirmed:
        return {"success": True, "message": "记忆已丢弃，不会保存"}

    # 生成 WHY 解释：为什么这个方案可行
    reasoning = _generate_reasoning(data)

    import memory_store as mem
    mem.save(
        user_input=data["user_input"],
        plan=data["plan"],
        result=data.get("result_summary", "成功"),
        step_results=data.get("step_results", []),
        tags=[],
        reasoning=reasoning,
    )
    return {"success": True, "message": "记忆已保存，下次可直接复用"}


def _generate_reasoning(data: dict) -> str:
    """
    用 LLM 生成 WHY 解释：为什么这个方案可行 / 为什么失败。
    这是「理解 WHY 比 HOW 重要」原则的实现。
    """
    user_input = data.get("user_input", "")
    plan = data.get("plan", [])
    step_results = data.get("step_results", [])
    had_failure = data.get("had_failure", False)

    plan_summary = "\n".join(
        f"  {i+1}. {s.get('action','')}: {s.get('description','')}"
        for i, s in enumerate(plan)
    )

    results_summary = ""
    for sr in step_results:
        step_num = sr.get("step", "?")
        action = sr.get("action", "")
        if "error" in sr:
            results_summary += f"  Step {step_num} ({action}): FAILED - {sr['error'][:100]}\n"
        else:
            r = sr.get("result", {})
            results_summary += f"  Step {step_num} ({action}): OK - {str(r)[:100]}\n"

    prompt = f"""分析以下任务执行，用 1-3 句话解释「为什么这个方案可行」或「为什么失败了」。
重点是原理和原因，不是步骤描述。

用户指令：{user_input}

执行方案：
{plan_summary}

执行结果：
{results_summary}

是否失败：{'是' if had_failure else '否'}

只输出原因分析，不要重复步骤。"""

    try:
        reasoning = _call_llm("你是一个执行结果分析器，专注于解释 WHY（原理和原因）。", prompt, temperature=0.1)
        return reasoning[:500] if reasoning else ""
    except Exception:
        return ""


def cleanup_expired_pending(max_age: int = 300):
    """清理过期（超过5分钟）的待确认记忆"""
    now = time.time()
    expired = [k for k, v in _pending_memories.items()
               if now - v.get("timestamp", 0) > max_age]
    for k in expired:
        _pending_memories.pop(k, None)


def _resolve_args(args: dict, step_context: dict) -> dict:
    """
    将步骤参数中的 {step_N.key} 替换为实际结果值。
    例如 {step_1.file_path} → "output/images/screenshot.png"
    """
    import re
    resolved = {}
    for key, value in args.items():
        if isinstance(value, str):
            def _replace_var(m):
                var_path = m.group(1)
                parts = var_path.split(".")
                ctx = step_context
                for part in parts:
                    if isinstance(ctx, dict) and part in ctx:
                        ctx = ctx[part]
                    else:
                        return m.group(0)  # keep original if not found
                return str(ctx) if not isinstance(ctx, (dict, list)) else json.dumps(ctx, ensure_ascii=False)
            resolved[key] = re.sub(r"\{([^}]+)\}", _replace_var, value)
        else:
            resolved[key] = value
    return resolved


async def _replan_remaining_steps(
    user_input: str,
    failed_step: int,
    failed_action: str,
    error: str,
    step_context: dict,
    remaining_plan: list[dict],
) -> list[dict] | None:
    """
    步骤失败后用 LLM 重新规划剩余步骤。
    将失败信息和已执行结果发给 LLM，生成替代方案。
    """
    # 构建已执行步骤摘要
    done_summary = []
    for key, val in sorted(step_context.items()):
        if "result" in val:
            r = val["result"]
            summary = str(r)[:200] if isinstance(r, dict) else str(r)[:200]
            done_summary.append(f"  Step {key}: {val['action']} -> {summary}")
        elif "error" in val:
            done_summary.append(f"  Step {key}: {val['action']} -> FAILED: {val['error'][:200]}")

    remaining_summary = "\n".join(
        f"  {s['step']}. {s.get('action','')}: {s.get('description','')}"
        for s in remaining_plan
    ) if remaining_plan else "  (无后续步骤)"

    prompt = f"""用户指令：{user_input}

第 {failed_step} 步执行失败：
  工具：{failed_action}
  错误：{error}

已完成的步骤：
{chr(10).join(done_summary) if done_summary else "  (无)"}

原计划的后续步骤：
{remaining_summary}

请分析失败原因，给出替代方案（JSON 数组格式，每个元素 {{"step":序号, "action":"工具名", "args":{{...}}, "description":"描述"}}）。
注意：
- 可以利用已完成的步骤结果
- 如果失败原因可修复，给出修复步骤
- 如果原路不通，换完全不同的方法
- 只输出 JSON 数组，不要其他文字"""

    llm_output = _call_llm("你是一个能诊断执行失败并给出替代方案的 AI。", prompt)
    if not llm_output:
        return None

    new_plan = _parse_plan(llm_output)
    return new_plan


# ========== 结果验证（P4） ==========

_VALIDATE_PROMPT = """你是一个执行结果验证器。判断一系列工具执行是否达成了用户的原始目标。

用户指令：{user_input}

执行方案：
{plan_summary}

执行结果：
{results_summary}

请评估：
1. 每个关键步骤是否成功完成
2. 整体目标是否达成
3. 是否有遗漏或需要补充的步骤

输出严格 JSON：
{{
  "passed": true/false,
  "score": 0-100（达成度百分比）,
  "step_checks": [
    {{"step": 1, "action": "xxx", "ok": true/false, "note": "简要说明"}}
  ],
  "summary": "一句话总结",
  "fix_suggestions": ["如果未通过，建议的修复步骤（可选）"]
}}

只输出 JSON，不要其他文字。"""


async def validate_result(
    user_input: str,
    plan: list[dict],
    step_results: list[dict],
) -> dict:
    """
    验证执行结果是否达成了用户目标。

    返回：
      {
        "passed": bool,
        "score": 0-100,
        "step_checks": [...],
        "summary": str,
        "fix_suggestions": [...]
      }
    """
    # 构建方案摘要
    plan_lines = []
    for i, step in enumerate(plan):
        plan_lines.append(f"  {i+1}. {step.get('action','')}: {step.get('description','')}")
    plan_summary = "\n".join(plan_lines)

    # 构建结果摘要
    result_lines = []
    for sr in step_results:
        step_num = sr.get("step", "?")
        action = sr.get("action", "")
        if "error" in sr:
            result_lines.append(f"  Step {step_num} ({action}): FAILED - {sr['error'][:200]}")
        else:
            r = sr.get("result", {})
            summary = str(r)[:300] if isinstance(r, dict) else str(r)[:300]
            result_lines.append(f"  Step {step_num} ({action}): OK - {summary}")
    results_summary = "\n".join(result_lines)

    prompt = _VALIDATE_PROMPT.format(
        user_input=user_input,
        plan_summary=plan_summary,
        results_summary=results_summary,
    )

    llm_output = _call_llm(
        "你是一个严格的执行结果验证器。",
        prompt,
        temperature=0.1,
    )

    if not llm_output:
        return {"passed": False, "score": 0, "summary": "验证器无响应", "step_checks": [], "fix_suggestions": []}

    # 解析 JSON
    text = llm_output.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1])

    try:
        result = json.loads(text)
        return {
            "passed": result.get("passed", False),
            "score": result.get("score", 0),
            "step_checks": result.get("step_checks", []),
            "summary": result.get("summary", ""),
            "fix_suggestions": result.get("fix_suggestions", []),
        }
    except json.JSONDecodeError:
        # 尝试从文本中提取 JSON
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                result = json.loads(match.group())
                return {
                    "passed": result.get("passed", False),
                    "score": result.get("score", 0),
                    "step_checks": result.get("step_checks", []),
                    "summary": result.get("summary", ""),
                    "fix_suggestions": result.get("fix_suggestions", []),
                }
            except json.JSONDecodeError:
                pass

    return {"passed": False, "score": 0, "summary": "验证结果解析失败", "step_checks": [], "fix_suggestions": []}


# 常见错误的关键词，命中后触发自动修复
_AUTO_FIX_PATTERNS = [
    "no module named", "module not found", "cannot import",
    "command not found", "not recognized",
    "pip", "not installed", "is not defined",
]


def _can_auto_fix(error: str) -> bool:
    """判断错误是否可能通过自动修复解决"""
    err_lower = str(error).lower()
    for pattern in _AUTO_FIX_PATTERNS:
        if pattern in err_lower:
            return True
    return False


async def _auto_fix(error: str) -> tuple[str, bool]:
    """尝试自动修复常见错误，返回 (修复描述, 是否成功)"""
    err_lower = str(error).lower()
    import re

    # 检查是否是不认识的命令（Windows 上缺工具）
    if "'zip'" in error or "'zip'" in err_lower or ("not recognized" in err_lower and "zip" in err_lower):
        try:
            import subprocess
            # 用 Python 的 zipfile 模块替代
            r = subprocess.run(
                ["python", "-c", "import zipfile; print('zipfile ok')"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                return "Windows 没有 zip 命令，将尝试用 Python 的 zipfile 模块替代", True
            return "Python zipfile 不可用", False
        except Exception:
            return "替代方案失败", False

    # 尝试提取缺少的 Python 包名
    pkg = None

    # "No module named 'xxx'"
    m = re.search(r"no module named ['\"]([^'\"]+)['\"]", err_lower, re.IGNORECASE)
    if m:
        pkg = m.group(1).split(".")[0]  # 取顶级包名

    # "ModuleNotFoundError: No module named 'xxx'"
    if not pkg:
        m = re.search(r"module not found.*?['\"]([^'\"]+)['\"]", err_lower, re.IGNORECASE)
        if m:
            pkg = m.group(1).split(".")[0]

    if pkg:
        try:
            import subprocess
            r = subprocess.run(
                ["pip", "install", pkg],
                capture_output=True, text=True, timeout=60
            )
            if r.returncode == 0:
                return f"已自动安装 {pkg}", True
            else:
                return f"尝试安装 {pkg} 失败：{r.stderr.strip()[:200]}", False
        except Exception as e:
            return f"自动安装失败：{str(e)[:200]}", False

    return "无法自动修复，将重试", True  # 让 retry 机制再试一次


# ========== 自学模式（Research → Learn → Plan） ==========

_RESEARCH_PROMPT = """你是一个自学型 AI 助手。用户要求你做一件你不太确定的事。

你的任务分两步：
1. 先判断是否需要搜索外部信息来了解怎么做
2. 如果需要，给出搜索关键词（1-3个不同角度的搜索词）

规则：
- 如果用户需求涉及到你不知道的具体工具/命令/API/操作 → 需要搜索
- 如果用户需求非常通用（如"写个程序"、"打开文件"）→ 不需要搜索
- 输出严格 JSON：{{"need_search": true/false, "queries": ["搜索词1", "搜索词2"], "reason": "为什么需要搜索"}}
- 如果 need_search 为 false，queries 为空数组即可"""

_RESEARCH_SYNTHESIS_PROMPT = """你是一个自学型 AI 助手。你刚刚搜索了相关信息，现在请根据搜索结果制定执行方案。

搜索结果：
{research}

用户指令：{user_input}

桌面环境：
{desktop_info}

{output_rules}

{tools}

请生成一个完整的步骤方案（JSON 数组）。
先理解搜索到的信息，再制定可行的步骤。
如果搜索结果中有具体命令/代码示例，直接使用它们。
只输出 JSON 数组，不要加其他文字。"""


async def _learn_and_plan(
    user_input: str,
    desktop_info: str,
    tools_text: str,
    output_rules: str,
    history_context: str = "",
) -> tuple[list[dict] | None, list[dict]]:
    """
    自学模式：
    1. 问 LLM 是否需要搜索
    2. 需要？→ 搜索 + 读结果 → 综合制定方案
    3. 不需要？→ 直接生成方案

    参数：
      history_context: 最近的对话历史摘要（用于理解上下文引用）

    返回：(plan, research_events)
    research_events 是用于前端展示的事件列表
    """
    research_events = []

    # === 第一步：判断是否需要搜索 ===
    research_prompt = _RESEARCH_PROMPT
    research_input = f"用户指令：{user_input}\n\n桌面环境：{desktop_info}\n\n可用工具：{tools_text}"
    if history_context:
        research_input = f"最近对话：\n{history_context}\n\n{research_input}"
    llm_output = _call_llm(research_prompt, research_input, temperature=0.1)

    need_search = False
    search_queries = []

    if llm_output:
        try:
            text = llm_output.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                if len(lines) >= 3:
                    text = "\n".join(lines[1:-1])
            decision = json.loads(text)
            need_search = decision.get("need_search", False)
            search_queries = decision.get("queries", [])
            if need_search and search_queries:
                research_events.append({
                    "type": "research_plan",
                    "reason": decision.get("reason", ""),
                    "queries": search_queries,
                })
            else:
                need_search = False
        except (json.JSONDecodeError, KeyError):
            need_search = False

    # === 第二步：搜索（如果需要） ===
    research_text = ""
    if need_search and search_queries:
        import asyncio

        async def search_one(query: str) -> str:
            result = await registry.execute("web_search", {"query": query, "max_results": 5})
            if isinstance(result, dict) and "results" in result:
                items = result["results"]
                urls = []
                snippets = []
                for r in items[:3]:
                    urls.append(r.get("url", ""))
                    snippets.append(f"- {r.get('title','')}: {r.get('snippet','')[:200]}")
                snippet_text = "\n".join(snippets)

                research_events.append({
                    "type": "research_result",
                    "query": query,
                    "results_count": len(items),
                    "snippets": [r.get("snippet","")[:120] for r in items[:3]],
                })

                page_texts = []
                for url in urls[:2]:
                    if not url:
                        continue
                    page = await registry.execute("web_fetch", {"url": url})
                    if isinstance(page, dict) and "content" in page:
                        page_texts.append(
                            f"[{page.get('title','')}]({url}):\n{page['content'][:2000]}"
                        )

                return (
                    f"搜索词：{query}\n摘要：\n{snippet_text}\n\n"
                    f"详细内容：\n{chr(10).join(page_texts)}"
                )
            return ""

        tasks = [search_one(q) for q in search_queries[:3]]
        results = await asyncio.gather(*tasks)
        research_text = "\n\n---\n\n".join(r for r in results if r)

        if research_text:
            research_events.append({"type": "research_done", "source_count": len(search_queries)})

    # === 2.5 GitHub 技能搜索：如果有现成 skill，拿来用而不是从零造 ===
    github_skill_info = ""
    if need_search:
        try:
            from self_learning import SelfLearningEngine
            sle = SelfLearningEngine()
            gh_skills = sle._search_github_skill_for_query(user_input)
            if gh_skills:
                # 尝试安装第一个匹配的
                best = gh_skills[0]
                research_events.append({
                    "type": "research_result",
                    "query": f"github:{best['repo']}",
                    "results_count": 1,
                    "snippets": [f"发现 GitHub 现成技能: {best['name']} ({best['repo']})"],
                })
                # 安装
                installed = await sle._install_skill(best)
                if installed:
                    skill_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "agent-skills", "skills", best["name"], "SKILL.md"
                    )
                    if os.path.isfile(skill_path):
                        with open(skill_path, "r", encoding="utf-8") as f:
                            skill_content = f.read()
                        github_skill_info = (
                            f"\n\n---\n从 GitHub 安装的现成技能 [{best['name']}]：\n"
                            f"{skill_content[:2000]}"
                        )
        except Exception:
            pass

    # === 第三步：生成方案 ===
    if research_text or github_skill_info:
        combined_research = (research_text or "") + github_skill_info
        synthesis_prompt = _RESEARCH_SYNTHESIS_PROMPT.format(
            research=combined_research,
            user_input=user_input,
            desktop_info=desktop_info,
            output_rules=output_rules,
            tools=tools_text,
        )
        plan_text = _call_llm(
            "你是一个能搜索信息并制定执行计划的 AI。",
            synthesis_prompt,
            temperature=0.1,
        )
    else:
        prompt = PLANNING_PROMPT.format(tools=tools_text, output_rules=output_rules)
        enriched_input = f"{desktop_info}\n\n用户指令：{user_input}"
        plan_text = _call_llm(prompt, enriched_input)

    if not plan_text:
        return None, research_events

    return _parse_plan(plan_text), research_events


async def process(
    user_input: str,
    memories: list[dict] | None = None,
    conversation_history: list[dict] | None = None,
) -> AsyncGenerator[dict, None]:
    """
    处理用户输入的模糊指令。

    参数：
      user_input: 用户当前输入
      memories: 预加载的记忆（可选）
      conversation_history: 最近 N 轮对话历史（用于理解上下文引用，如"刚才那个文件"）

    流程：
      查记忆 → 命中？→ 执行记住的方案
              → 没命中？→ LLM 生成方案 → 执行 → 记住
    """
    # === 1. 查记忆 ===
    if memories is None:
        memories = mem.search(user_input)

    # 相似度阈值：低于此值认为是不相关记忆，走自学路径
    SIMILARITY_THRESHOLD = 0.6

    if memories:
        best = memories[0]
        cosine_sim = best.get("_cosine_sim", 0.0)
        exact_match = best.get("user_input", "").strip().lower() == user_input.strip().lower()

        yield {
            "type": "memory_hit",
            "entry_id": best["id"],
            "user_input": best["user_input"],
            "plan": best.get("plan", []),
            "confidence": "high" if exact_match else "similar",
            "cosine_sim": cosine_sim,
            "above_threshold": exact_match or cosine_sim >= SIMILARITY_THRESHOLD,
        }

        # 只有精确匹配或高相似度才用记忆，否则走自学
        if exact_match or cosine_sim >= SIMILARITY_THRESHOLD:
            plan = best.get("plan", [])
            mem.record_hit(best["id"])
            if plan:
                async for event in execute_plan(plan, user_input=user_input):
                    yield event
                return

    # === 2. 没命中 → 学习模式 ===
    yield {"type": "learning", "message": "记忆中没找到现成方案，开始自学..."}

    # 收集桌面环境信息，让 LLM 了解当前状态
    desktop_info = desktop_context.describe_desktop()
    yield {"type": "context", "content": desktop_info}

    # 2a. 生成方案（自学模式：不确定就去搜索再回来制定方案）
    tools_text = _get_tool_summary()
    output_rules = output_mgr.describe_structure()

    # 构建包含对话历史的上下文
    history_context = ""
    if conversation_history:
        recent = conversation_history[-6:]  # 最近 3 轮
        history_lines = []
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]
            history_lines.append(f"[{role}]: {content}")
        history_context = "\n".join(history_lines)

    plan, research_events = await _learn_and_plan(
        user_input, desktop_info, tools_text, output_rules,
        history_context=history_context,
    )

    # 输出研究过程事件（如果有）
    for evt in research_events:
        yield evt

    if not plan:
        yield {"type": "error", "content": "无法生成执行方案，请稍后再试"}
        return

    yield {
        "type": "plan_generated",
        "plan": plan,
        "steps_count": len(plan),
    }

    # 2b. 执行方案
    step_results = []
    had_failure = False

    async for event in execute_plan(plan, user_input=user_input):
        if event["type"] == "step_result":
            step_results.append({
                "step": event["step"],
                "action": event["action"],
                "result": event["result"],
            })
        elif event["type"] == "step_failed":
            had_failure = True
            step_results.append({
                "step": event["step"],
                "action": event["action"],
                "error": event["error"],
            })
        elif event["type"] == "step_retry":
            pass  # 重试中，不标记失败（最终成功不算失败）
        yield event

    # 2c. 结果验证
    validation = await validate_result(user_input, plan, step_results)
    yield {
        "type": "validation",
        "passed": validation["passed"],
        "score": validation["score"],
        "summary": validation["summary"],
        "step_checks": validation["step_checks"],
        "fix_suggestions": validation.get("fix_suggestions", []),
    }

    # 如果验证未通过且有修复建议，尝试自动修复
    if not validation["passed"] and validation.get("fix_suggestions"):
        fix_suggestions = validation["fix_suggestions"]
        yield {
            "type": "auto_fix_attempt",
            "reason": validation["summary"],
            "fix_count": len(fix_suggestions),
        }

        # 将修复建议作为新方案执行
        fix_plan = []
        for i, suggestion in enumerate(fix_suggestions[:5]):
            fix_plan.append({
                "step": i + 1,
                "action": "execute_python",
                "args": {"code": f"# 修复建议: {suggestion}\nprint('TODO: implement fix')"},
                "description": f"修复: {suggestion}",
            })

        # 用 LLM 将修复建议转为可执行步骤
        fix_prompt = f"""用户指令：{user_input}

执行失败原因：{validation['summary']}

修复建议：
{chr(10).join(f'- {s}' for s in fix_suggestions)}

请将修复建议转为可执行的步骤（JSON 数组格式）。
只输出 JSON 数组。"""

        fix_text = _call_llm("你是执行方案修复器。", fix_prompt, temperature=0.1)
        fix_plan = _parse_plan(fix_text)

        if fix_plan:
            yield {
                "type": "fix_plan_generated",
                "plan": fix_plan,
                "steps_count": len(fix_plan),
            }

            fix_results = []
            async for event in execute_plan(fix_plan, user_input=user_input):
                if event["type"] == "step_result":
                    fix_results.append({
                        "step": event["step"],
                        "action": event["action"],
                        "result": event["result"],
                    })
                elif event["type"] == "step_failed":
                    fix_results.append({
                        "step": event["step"],
                        "action": event["action"],
                        "error": event["error"],
                    })
                yield event

            # 合并结果
            step_results.extend(fix_results)
            # 重新验证
            revalidation = await validate_result(user_input, plan + fix_plan, step_results)
            yield {
                "type": "revalidation",
                "passed": revalidation["passed"],
                "score": revalidation["score"],
                "summary": revalidation["summary"],
            }
            if revalidation["passed"]:
                had_failure = False

    # 2d. 询问用户确认后再保存
    import uuid as _uuid
    pending_id = str(_uuid.uuid4())[:8]
    result_summary = "成功" if not had_failure else "部分完成（有步骤失败）"
    _pending_memories[pending_id] = {
        "user_input": user_input,
        "plan": plan,
        "step_results": step_results,
        "had_failure": had_failure,
        "result_summary": result_summary,
        "timestamp": time.time(),
    }
    yield {
        "type": "memory_confirm",
        "pending_id": pending_id,
        "user_input": user_input,
        "step_results": step_results,
        "plan": plan,
        "result_summary": result_summary,
        "step_count": len(step_results),
        "had_failure": had_failure,
    }
