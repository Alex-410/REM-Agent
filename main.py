import json
import uuid
import os
from typing import Optional

from fastapi import FastAPI, Request, Query
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import (
    run_agent, parse_command, handle_command,
    skill_engine, persona_manager,
)
from workflow_state import WorkflowManager
from self_learning import SelfLearningEngine
from task_manager import get_task_manager, Task, TaskStatus

app = FastAPI(title="Big Agent — Skill-Aware AI Engineering Agent")

# 自学引擎（启动后自动在后台学新技能）
self_learning = SelfLearningEngine()

# 任务管理器
task_manager = get_task_manager()

# Static files
os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
conversations: dict[str, list] = {}
workflow_manager = WorkflowManager()


# --- Models ---

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = ""


class PersonaSwitchRequest(BaseModel):
    persona: str
    conversation_id: str = ""


class SkillActivateRequest(BaseModel):
    skill: str
    conversation_id: str = ""


class MemoryConfirmRequest(BaseModel):
    pending_id: str
    confirmed: bool = True


# --- Routes ---

@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/memory")
async def memory_page():
    return FileResponse("static/memory.html")

@app.get("/learning")
async def learning_page():
    return FileResponse("static/learning.html")


# --- Tool info ---

@app.get("/api/tools")
async def list_tools():
    from agent import registry
    defs = registry.get_definitions()
    return {
        "tools": [d["function"]["name"] for d in defs],
        "count": len(defs),
        "details": defs,
    }


# --- Personas ---

@app.get("/api/personas")
async def list_personas():
    return {
        "personas": [p.to_dict() for p in persona_manager.get_all_personas()],
        "current": persona_manager.current,
    }


@app.post("/api/persona/switch")
async def switch_persona(req: PersonaSwitchRequest):
    persona = persona_manager.switch_to(req.persona)
    if persona:
        # Also update workflow state persona if conversation exists
        wf = workflow_manager.get(req.conversation_id) if req.conversation_id else None
        return {
            "success": True,
            "persona": persona.to_dict(),
            "message": f"Switched to {persona.name} persona.",
        }
    return {
        "success": False,
        "message": f"Persona '{req.persona}' not found.",
        "available": [p.name for p in persona_manager.get_all_personas()],
    }


# --- Skills ---

@app.get("/api/skills")
async def list_skills(phase: str = "", include_archived: bool = False):
    if phase:
        skills = skill_engine.get_skills_by_phase(phase)
    else:
        skills = skill_engine.get_all_skills(include_archived=include_archived)
    return {
        "skills": [s.to_dict() for s in skills],
        "count": len(skills),
    }


@app.get("/api/skills/inventory")
async def skill_inventory():
    """查询完整技能清单：会什么、从哪来、状态如何"""
    return self_learning.get_manifest()


@app.get("/api/skills/summary")
async def skill_summary():
    """简版技能列表，方便快速查看"""
    return {"skills": self_learning.get_skills_summary()}


@app.post("/api/learn")
async def trigger_learning(topic: str = ""):
    """手动触发一次学习。不传 topic 则全量检查，传 topic 则自学指定主题"""
    import json
    result = await self_learning.learn_now(topic)
    return {"success": True, "result": result}


@app.get("/api/skills/match")
async def match_skills(query: str = Query("", description="User input to match against skills")):
    if not query:
        return {"matches": [], "count": 0}
    matches = skill_engine.find_matching_skills(query)
    return {
        "matches": [m.to_dict() for m in matches],
        "count": len(matches),
    }


@app.post("/api/skill/activate")
async def activate_skill(req: SkillActivateRequest):
    skill = skill_engine.get_skill(req.skill)
    if not skill:
        matches = skill_engine.find_matching_skills(req.skill)
        if matches:
            return {
                "success": False,
                "message": f"Skill '{req.skill}' not found. Did you mean: {', '.join(m.name for m in matches[:3])}?",
                "suggestions": [m.to_dict() for m in matches[:3]],
            }
        return {"success": False, "message": f"Skill '{req.skill}' not found."}

    if req.conversation_id:
        wf = workflow_manager.get_or_create(req.conversation_id)
        wf.set_phase(skill.phase)
        wf.set_skill(skill.name)

    return {
        "success": True,
        "skill": skill.to_dict(),
        "message": f"Activated skill: {skill.name} ({skill.phase} phase).",
    }


# --- Workflow ---

@app.get("/api/workflow")
async def get_workflow(conversation_id: str = "default"):
    wf = workflow_manager.get_or_create(conversation_id)
    return wf.to_dict()


@app.post("/api/workflow/reset")
async def reset_workflow(conversation_id: str = "default"):
    wf = workflow_manager.get_or_create(conversation_id)
    wf.reset()
    return {"success": True, "message": "Workflow reset."}


# --- Intent Engine (with Task Tracking) ---

@app.post("/api/intent")
async def intent_chat(req: ChatRequest):
    """
    意图引擎接口：接收模糊指令，自动拆解步骤并执行。
    自动创建后台任务，支持进度查询。
    """
    conv_id = req.conversation_id or str(uuid.uuid4())
    user_message = req.message.strip()

    # 创建后台任务
    task = task_manager.create(user_message)

    async def event_stream():
        nonlocal task
        try:
            from intent_engine import process
            async for event in process(user_message):
                event["conversation_id"] = conv_id
                event["task_id"] = task.id

                # 更新任务进度
                etype = event.get("type", "")
                if etype == "plan_generated":
                    task.total_steps = event.get("steps_count", 0)
                elif etype == "step":
                    task.update_progress(
                        event.get("step", 0),
                        event.get("total", 0),
                        f"{event.get('action','')} — {event.get('description','')}",
                    )
                elif etype == "steps_done":
                    task.mark_completed("成功")
                elif etype == "step_failed":
                    task.mark_failed(event.get("error", "未知错误"))
                elif etype == "error":
                    task.mark_failed(event.get("content", "未知错误"))

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            task.mark_failed(str(e)[:500])
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)[:500], 'conversation_id': conv_id, 'task_id': task.id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# --- Task Management APIs ---

@app.get("/api/tasks")
async def list_tasks(limit: int = Query(20, description="返回条数"), active_only: bool = Query(False, description="只显示运行中的任务")):
    """列出所有任务（按创建时间倒序）"""
    if active_only:
        tasks = task_manager.active_tasks()
    else:
        tasks = task_manager.all_tasks(limit=limit)
    return {
        "tasks": [t.to_dict() for t in tasks],
        "count": len(tasks),
        "active_count": len(task_manager.active_tasks()),
    }


@app.get("/api/task/{task_id}")
async def get_task(task_id: str):
    """查询单个任务的状态和结果"""
    task = task_manager.get(task_id)
    if not task:
        return {"error": "Task not found", "task_id": task_id}, 404
    return task.to_dict()


@app.post("/api/task/cancel/{task_id}")
async def cancel_task(task_id: str):
    """取消一个正在运行的任务"""
    task = task_manager.get(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    if task.status != TaskStatus.RUNNING:
        return {"error": f"Task is {task.status.value}, cannot cancel"}, 400
    task.mark_cancelled()
    return {"success": True, "task_id": task_id, "status": "cancelled"}


@app.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    """删除一个任务记录"""
    ok = task_manager.remove(task_id)
    return {"success": ok, "task_id": task_id}


# --- Chat ---

@app.post("/api/chat")
async def chat(req: ChatRequest):
    conv_id = req.conversation_id or str(uuid.uuid4())
    user_message = req.message.strip()

    if conv_id not in conversations:
        conversations[conv_id] = []

    # Get or create workflow state
    wf = workflow_manager.get_or_create(conv_id)

    # Check for slash commands
    cmd = parse_command(user_message)
    if cmd:
        response_text = handle_command(cmd, wf)
        conversations[conv_id].append({"role": "user", "content": user_message})
        conversations[conv_id].append({"role": "assistant", "content": response_text})

        async def command_stream():
            yield f"data: {json.dumps({'type': 'text', 'content': response_text, 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            command_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    # Auto-detect skill from message if no active skill
    if not wf.active_skill:
        matches = skill_engine.find_matching_skills(user_message)
        if matches:
            best = matches[0]
            wf.set_phase(best.phase)
            wf.set_skill(best.name)
            # Set goal from user message
            wf.set_goal(user_message[:200])

    # Store user message
    conversations[conv_id].append({"role": "user", "content": user_message})

    async def event_stream():
        try:
            async for event in run_agent(conversations[conv_id], wf):
                event["conversation_id"] = conv_id
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)[:500], 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# --- Conversation management ---

@app.get("/api/conversations")
async def list_conversations():
    return {
        "conversations": list(conversations.keys()),
        "count": len(conversations),
    }


@app.post("/api/clear")
async def clear_conversation(conversation_id: str = "default"):
    if conversation_id in conversations:
        conversations[conversation_id] = []
    workflow_manager.get_or_create(conversation_id).reset()
    return {"status": "ok", "conversation_id": conversation_id}


# --- Memory management ---

@app.get("/api/memory")
async def memory_stats():
    import memory_store as mem
    return mem.stats()


@app.get("/api/memory/search")
async def memory_search(query: str = Query("", description="搜索关键词")):
    import memory_store as mem
    if not query:
        return {"results": [], "count": 0}
    results = mem.search(query, top_k=10)
    return {
        "results": [
            {
                "id": r["id"],
                "user_input": r["user_input"],
                "plan": r.get("plan", []),
                "step_results": r.get("step_results", []),
                "result": r["result"],
                "hit_count": r.get("hit_count", 0),
                "keywords": r.get("keywords", []),
                "has_vector": r.get("has_vector", False),
                "updated_at": r.get("updated_at", 0),
            }
            for r in results
        ],
        "count": len(results),
    }


@app.post("/api/memory/rebuild")
async def memory_rebuild():
    import memory_store as mem
    return mem.rebuild_vectors()


@app.post("/api/memory/delete")
async def memory_delete(entry_id: str = Query("", description="记忆 ID")):
    import memory_store as mem
    if entry_id:
        mem.delete(entry_id)
        return {"success": True}
    return {"success": False, "message": "No entry_id provided"}


@app.post("/api/memory/confirm")
async def confirm_memory(req: MemoryConfirmRequest):
    """用户确认/拒绝保存记忆"""
    from intent_engine import confirm_memory as do_confirm
    return do_confirm(req.pending_id, confirmed=req.confirmed)


# --- Learning Log ---

@app.get("/api/learning/log")
async def learning_log(limit: int = Query(50, description="返回条数")):
    """查看学习记录：学过什么、从哪学的、什么时候学的"""
    logs = self_learning.get_learning_log(limit)
    return {
        "total": len(logs),
        "logs": logs,
    }


@app.on_event("startup")
async def start_self_learning():
    """应用启动时自动开启后台自学"""
    await self_learning.start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
