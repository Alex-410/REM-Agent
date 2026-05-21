import json
import os
from datetime import datetime
from typing import Optional

from skill_engine import PHASE_ORDER, PHASE_LABELS, PHASE_EMOJIS


class WorkflowState:
    """Tracks the current development workflow state for a conversation."""

    def __init__(self, conversation_id: str = ""):
        self.conversation_id = conversation_id
        self.current_phase: str = ""  # One of: define, plan, build, verify, review, ship
        self.active_skill: str = ""  # Currently active skill name
        self.completed_phases: list[str] = []
        self.completed_skills: list[str] = []
        self.tasks: list[dict] = []
        self.goal: str = ""  # High-level goal of the conversation
        self.project_context: str = ""  # Project info gathered during conversation
        self.started_at: str = datetime.now().isoformat()
        self.updated_at: str = self.started_at

    def set_phase(self, phase: str):
        if phase in PHASE_ORDER or phase == "meta":
            if self.current_phase and self.current_phase != phase:
                self.completed_phases.append(self.current_phase)
            self.current_phase = phase
            self.updated_at = datetime.now().isoformat()

    def set_skill(self, skill_name: str):
        if self.active_skill and self.active_skill != skill_name:
            self.completed_skills.append(self.active_skill)
        self.active_skill = skill_name
        self.updated_at = datetime.now().isoformat()

    def set_goal(self, goal: str):
        self.goal = goal
        self.updated_at = datetime.now().isoformat()

    def add_task(self, title: str, acceptance: str = "", status: str = "pending"):
        self.tasks.append({
            "id": len(self.tasks) + 1,
            "title": title,
            "acceptance": acceptance,
            "status": status,
        })
        self.updated_at = datetime.now().isoformat()

    def update_task(self, task_id: int, status: str):
        for task in self.tasks:
            if task["id"] == task_id:
                task["status"] = status
                break
        self.updated_at = datetime.now().isoformat()

    def reset(self):
        self.current_phase = ""
        self.active_skill = ""
        self.completed_phases = []
        self.completed_skills = []
        self.tasks = []
        self.goal = ""
        self.project_context = ""
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "current_phase": self.current_phase,
            "current_phase_label": PHASE_LABELS.get(self.current_phase, ""),
            "current_phase_emoji": PHASE_EMOJIS.get(self.current_phase, ""),
            "active_skill": self.active_skill,
            "completed_phases": self.completed_phases,
            "completed_skills": self.completed_skills,
            "tasks": self.tasks,
            "goal": self.goal,
            "phase_order": [
                {"id": p, "label": PHASE_LABELS.get(p, p), "emoji": PHASE_EMOJIS.get(p, ""),
                 "completed": p in self.completed_phases,
                 "active": p == self.current_phase}
                for p in PHASE_ORDER
            ],
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }

    def get_phase_prompt(self) -> str:
        """Generate a system prompt fragment for the current workflow state."""
        parts = []

        if self.goal:
            parts.append(f"Current goal: {self.goal}")

        if self.current_phase:
            emoji = PHASE_EMOJIS.get(self.current_phase, "")
            label = PHASE_LABELS.get(self.current_phase, self.current_phase)
            parts.append(f"Current phase: {emoji} {label}")

        if self.active_skill:
            parts.append(f"Active skill: {self.active_skill}")

        if self.tasks:
            pending = [t for t in self.tasks if t["status"] == "pending"]
            done = [t for t in self.tasks if t["status"] == "done"]
            if pending:
                parts.append(f"Pending tasks: {len(pending)}")
            if done:
                parts.append(f"Completed tasks: {len(done)}")

        if self.completed_phases:
            labels = [f"{PHASE_EMOJIS.get(p, '')}{PHASE_LABELS.get(p, p)}"
                      for p in self.completed_phases]
            parts.append(f"Completed phases: {', '.join(labels)}")

        return "\n".join(parts) if parts else ""


class WorkflowManager:
    """Manages workflow states across multiple conversations."""

    def __init__(self):
        self.conversations: dict[str, WorkflowState] = {}

    def get_or_create(self, conv_id: str) -> WorkflowState:
        if conv_id not in self.conversations:
            self.conversations[conv_id] = WorkflowState(conv_id)
        return self.conversations[conv_id]

    def get(self, conv_id: str) -> Optional[WorkflowState]:
        return self.conversations.get(conv_id)

    def delete(self, conv_id: str):
        self.conversations.pop(conv_id, None)

    def reset_all(self):
        self.conversations.clear()
