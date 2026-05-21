import json
from typing import AsyncGenerator

import httpx
from openai import OpenAI

import config
from tools import register_all_tools
from tools.registry import ToolRegistry
from skill_engine import SkillEngine, PHASE_ORDER, PHASE_LABELS, PHASE_EMOJIS
from persona_manager import PersonaManager
from workflow_state import WorkflowState

registry = ToolRegistry()
register_all_tools(registry)

skill_engine = SkillEngine()
persona_manager = PersonaManager()


def build_system_prompt(wf: WorkflowState | None = None) -> str:
    """Dynamically build a system prompt based on workflow state and persona."""
    persona = persona_manager.get_current()
    phase = wf.current_phase if wf else ""
    active_skill = wf.active_skill if wf else ""

    sections = []

    # 1. Core identity
    if persona.name == "general":
        sections.append("""You are an expert AI Software Engineering Agent. You have deep knowledge of the full software development lifecycle.

CORE RULES:
1. You have access to tools — use them proactively. When asked a question that requires up-to-date info, search the web.
2. Respond in Chinese unless asked otherwise.
3. Keep responses concise and actionable.
4. Think step by step before using tools.
5. When the task is complex, break it into steps and work through them one at a time.
6. After completing a task, summarize what was done and suggest next steps.

TOOL USE:
- web_search / web_fetch: For any knowledge questions, current info, news, facts
- execute_python: For calculations, data analysis, automation
- bash: For shell commands, git operations, build tools
- read_file / write_file / list_files: For file operations
- image_search / image_fetch: For finding and saving images
- code_search: For searching codebases
- git_status / git_diff / git_log / git_commit: For git operations
- project_structure: For analyzing project layout""")
    else:
        # Persona-specific identity comes from the persona content
        sections.append(persona.content)

    # 2. Workflow / lifecycle awareness
    sections.append("""
DEVELOPMENT LIFECYCLE:
I recognize these development phases and can guide users through them:
📋 Define → 🗺️ Plan → 🔧 Build → ✅ Verify → 👁️ Review → 🚀 Ship

Users can use slash commands:
/spec — Write a specification
/plan — Break down into tasks
/build — Implement incrementally
/test — Write and run tests
/review — Code review
/ship — Prepare for deployment
/phase <name> — Set current phase
/skill <name> — Activate a skill
/persona <name> — Switch persona (general, code-reviewer, security-auditor, test-engineer)
/status — Show current workflow state
/reset — Reset workflow state""")

    # 3. Current workflow state
    if wf:
        workflow_context = wf.get_phase_prompt()
        if workflow_context:
            sections.append(f"CURRENT WORKFLOW STATE:\n{workflow_context}")

    # 4. Active skill instructions
    if active_skill:
        skill_prompt = skill_engine.get_active_skill_prompt(active_skill)
        if skill_prompt:
            sections.append(skill_prompt)

    # 5. Available tools
    tool_names = [d["function"]["name"] for d in registry.get_definitions()]
    sections.append(f"AVAILABLE TOOLS ({len(tool_names)}): {', '.join(sorted(tool_names))}")

    return "\n\n---\n\n".join(sections)


async def run_agent(
    messages: list,
    wf: WorkflowState | None = None,
) -> AsyncGenerator[dict, None]:
    """Run the agent with dynamic system prompt."""
    client = OpenAI(
        api_key=config.DEEPSEEK_API_KEY,
        base_url=config.DEEPSEEK_BASE_URL,
        http_client=httpx.Client(trust_env=False),
    )

    # Build and inject system prompt
    system_prompt = build_system_prompt(wf)
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": system_prompt})
    else:
        messages[0]["content"] = system_prompt

    iteration = 0
    while iteration < config.MAX_ITERATIONS:
        try:
            import os, uuid
            _debug_id = str(uuid.uuid4())[:8]
            _log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_api.log")
            with open(_log_path, "a", encoding="utf-8") as df:
                df.write(f"[{_debug_id}] Call iteration={iteration}, msgs={len(messages)}:")
                for mi, m in enumerate(messages):
                    has_tc = "tool_calls" in m
                    tc_count = len(m.get("tool_calls", [])) if has_tc else 0
                    is_tool = m.get("role") == "tool"
                    df.write(f" [{mi}]{m.get('role')}|tc={tc_count}|tool={is_tool}")
                df.write(f"\n")
            response = client.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                messages=messages,
                tools=registry.get_definitions(),
                stream=False,
                timeout=config.TOOL_TIMEOUT,
            )
        except Exception as e:
            # 报错时清理未配对的 tool_calls，防止历史消息污染下次请求
            invalid_starts = [i for i, m in enumerate(messages)
                              if m.get("tool_calls") and not any(
                                  t.get("role") == "tool" and t.get("tool_call_id") in {tc["id"] for tc in m["tool_calls"]}
                                  for t in messages[i+1:]
                              )]
            for idx in reversed(invalid_starts):
                del messages[idx]
            yield {"type": "error", "content": f"API call failed: {str(e)}"}
            return

        choice = response.choices[0]
        msg = choice.message

        if msg.content:
            yield {"type": "text", "content": msg.content}

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            # DeepSeek 思考模式：reasoning_content 必须原样回传
            # 所以用 model_dump() 保留全部字段(含 reasoning_content)，只弹掉废弃的 function_call
            # DEBUG_V2: model_dump only pop function_call
            msg_dict = msg.model_dump()
            msg_dict.pop("function_call", None)
            messages.append(msg_dict)

            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {"_raw": tc.function.arguments}

                yield {
                    "type": "tool_call",
                    "id": tc.id,
                    "tool": tc.function.name,
                    "args": args,
                }

                try:
                    result = await registry.execute(tc.function.name, args)
                except Exception as tool_err:
                    result = {"error": str(tool_err)}
                result_str = json.dumps(result, ensure_ascii=False, default=str)

                if len(result_str) > config.MAX_TOOL_RESULT_LENGTH:
                    result_str = result_str[:config.MAX_TOOL_RESULT_LENGTH] + "..."

                yield {
                    "type": "tool_result",
                    "id": tc.id,
                    "tool": tc.function.name,
                    "result": result_str,
                }

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })

            iteration += 1
        else:
            messages.append({"role": "assistant", "content": msg.content or ""})
            yield {"type": "done"}
            return

    yield {"type": "error", "content": "Reached maximum iterations. Task may be too complex."}


def parse_command(text: str) -> dict | None:
    """Parse slash commands from user input. Returns command dict or None."""
    text = text.strip()

    # /do — 意图引擎：模糊指令执行
    if text.lower().startswith("/do"):
        return {"cmd": "do", "args": text[3:].strip()}

    # /spec
    if text.lower().startswith("/spec"):
        return {"cmd": "spec", "args": text[5:].strip()}

    # /plan
    if text.lower().startswith("/plan"):
        return {"cmd": "plan", "args": text[5:].strip()}

    # /build
    if text.lower().startswith("/build"):
        return {"cmd": "build", "args": text[6:].strip()}

    # /test
    if text.lower().startswith("/test"):
        return {"cmd": "test", "args": text[5:].strip()}

    # /review
    if text.lower().startswith("/review"):
        return {"cmd": "review", "args": text[7:].strip()}

    # /ship
    if text.lower().startswith("/ship"):
        return {"cmd": "ship", "args": text[5:].strip()}

    # /skill <name>
    m = __import__("re").match(r"^/skill\s+(\S+)", text, __import__("re").IGNORECASE)
    if m:
        return {"cmd": "skill", "args": m.group(1)}

    # /persona <name>
    m = __import__("re").match(r"^/persona\s+(\S+)", text, __import__("re").IGNORECASE)
    if m:
        return {"cmd": "persona", "args": m.group(1)}

    # /phase <name>
    m = __import__("re").match(r"^/phase\s+(\S+)", text, __import__("re").IGNORECASE)
    if m:
        return {"cmd": "phase", "args": m.group(1)}

    # /status
    if text.lower().startswith("/status"):
        return {"cmd": "status", "args": ""}

    # /reset
    if text.lower().startswith("/reset"):
        return {"cmd": "reset", "args": ""}

    # /help
    if text.lower().startswith("/help"):
        return {"cmd": "help", "args": ""}

    return None


def handle_command(cmd: dict, wf: WorkflowState) -> str:
    """Handle a parsed command and update workflow state. Returns response text."""
    cmd_type = cmd["cmd"]
    args = cmd["args"]

    if cmd_type == "spec":
        wf.set_phase("define")
        wf.set_skill("spec-driven-development")
        return (
            "📋 **Spec-Driven Development** activated!\n\n"
            "Let's write a specification. Tell me what you want to build:\n"
            "- What's the feature/project?\n"
            "- Who is the user?\n"
            "- What does success look like?\n\n"
            "I'll help you define objectives, tech stack, structure, and acceptance criteria."
        )

    if cmd_type == "plan":
        wf.set_phase("plan")
        wf.set_skill("planning-and-task-breakdown")
        return (
            "🗺️ **Planning & Task Breakdown** activated!\n\n"
            "I'll help break down your feature into small, verifiable tasks. "
            "Please share your spec or describe what you want to build, and I'll:\n"
            "1. Identify the dependency graph\n"
            "2. Slice into vertical tasks\n"
            "3. Add acceptance criteria and verification steps"
        )

    if cmd_type == "build":
        wf.set_phase("build")
        wf.set_skill("incremental-implementation")
        return (
            "🔧 **Incremental Implementation** activated!\n\n"
            "I'll build in thin vertical slices — implement, test, verify, commit, repeat. "
            "Share the task or feature you want me to implement."
        )

    if cmd_type == "test":
        wf.set_phase("verify")
        wf.set_skill("test-driven-development")
        return (
            "✅ **Test-Driven Development** activated!\n\n"
            "I'll follow Red-Green-Refactor. Share the code or feature you want tests for."
        )

    if cmd_type == "review":
        wf.set_phase("review")
        wf.set_skill("code-review-and-quality")
        return (
            "👁️ **Code Review** activated!\n\n"
            "I'll review code across five axes: correctness, readability, architecture, security, performance. "
            "Share the diff or files you want reviewed."
        )

    if cmd_type == "ship":
        wf.set_phase("ship")
        wf.set_skill("shipping-and-launch")
        return (
            "🚀 **Shipping & Launch** activated!\n\n"
            "I'll help prepare for deployment with a pre-launch checklist, "
            "rollback plan, and monitoring setup. What are we shipping?"
        )

    if cmd_type == "skill":
        skill = skill_engine.get_skill(args)
        if skill:
            wf.set_phase(skill.phase)
            wf.set_skill(skill.name)
            emoji = PHASE_EMOJIS.get(skill.phase, "📌")
            return (
                f"{emoji} Skill **{skill.name}** activated! ({PHASE_LABELS.get(skill.phase, skill.phase)} phase)\n\n"
                f"{skill.description}\n\n"
                f"I'll follow this skill's workflow. How would you like to start?"
            )
        # Try fuzzy match
        matches = skill_engine.find_matching_skills(args)
        if matches:
            names = "\n".join(f"  - `{s.name}` ({s.description[:60]}...)" for s in matches[:5])
            return (
                f"Skill '{args}' not found. Did you mean one of these?\n{names}\n\n"
                f"Use `/skill <name>` to activate one."
            )
        return f"Skill '{args}' not found. Use `/skill <name>` with a valid skill name."

    if cmd_type == "persona":
        persona = persona_manager.get_persona(args)
        if persona:
            persona_manager.switch_to(args)
            return (
                f"🔄 Switched to persona **{persona.name}** ({persona.role}).\n"
                f"{persona.description}"
            )
        available = ", ".join(p.name for p in persona_manager.get_all_personas())
        return f"Persona '{args}' not found. Available: {available}"

    if cmd_type == "phase":
        if args in PHASE_ORDER or args == "meta":
            wf.set_phase(args)
            emoji = PHASE_EMOJIS.get(args, "")
            label = PHASE_LABELS.get(args, args)
            return f"{emoji} Switched to **{label}** phase."
        return f"Phase '{args}' not valid. Options: {', '.join(PHASE_ORDER)}"

    if cmd_type == "status":
        state = wf.to_dict()
        lines = [f"**Workflow Status** ({state['conversation_id'][:8]}...)"]
        if state["goal"]:
            lines.append(f"\n🎯 **Goal:** {state['goal']}")
        if state["current_phase"]:
            lines.append(f"\n📍 **Phase:** {state['current_phase_emoji']} {state['current_phase_label']}")
        if state["active_skill"]:
            lines.append(f"📖 **Active Skill:** {state['active_skill']}")
        if state["completed_phases"]:
            completed = [f"{p['emoji']} {p['label']}" for p in state["phase_order"] if p["completed"]]
            lines.append(f"✅ **Completed Phases:** {', '.join(completed)}")
        lines.append(f"\n📊 **Phase Progress:**")
        for p in state["phase_order"]:
            mark = "✅" if p["completed"] else ("▶️" if p["active"] else "⬜")
            lines.append(f"  {mark} {p['emoji']} {p['label']}")
        if state["tasks"]:
            lines.append(f"\n📋 **Tasks:**")
            for t in state["tasks"]:
                status_mark = "✅" if t["status"] == "done" else "⬜"
                lines.append(f"  {status_mark} #{t['id']} {t['title']}")
        lines.append(f"\n👤 **Persona:** {persona_manager.get_current().name}")
        lines.append(f"⚙️ **Tools available:** {len(registry.get_definitions())}")
        return "\n".join(lines)

    if cmd_type == "reset":
        wf.reset()
        return "🔄 Workflow state has been reset."

    if cmd_type == "do":
        return (
            "🤖 **意图引擎** activated!\n\n"
            "我会理解你的模糊指令，自己拆解步骤并执行。\n"
            "例如：\n"
            "  `/do 写个爱心代码`\n"
            "  `/do 帮我创建一个 test 文件夹`\n"
            "  `/do 给张三发微信说晚上一起吃饭`\n\n"
            "请描述你想让我做什么。"
        )

    if cmd_type == "help":
        return (
            "**Available Commands:**\n\n"
            "**Phases:**\n"
            "  `/spec` — 写需求文档\n"
            "  `/plan` — 拆任务\n"
            "  `/build` — 开始构建\n"
            "  `/test` — 写/跑测试\n"
            "  `/review` — 代码审查\n"
            "  `/ship` — 准备发布\n\n"
            "**Action:**\n"
            "  `/do <指令>` — 意图引擎：用模糊指令控制电脑\n\n"
            "**Control:**\n"
            "  `/skill <name>` — 激活一个技能\n"
            "  `/persona <name>` — 切换角色\n"
            "  `/phase <name>` — 设置开发阶段\n"
            "  `/status` — 查看当前状态\n"
            "  `/reset` — 重置状态\n"
            "  `/help` — 显示帮助\n\n"
            "**Personas:** " + ", ".join(p.name for p in persona_manager.get_all_personas())
        )

    return ""
