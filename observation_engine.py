"""
观察引擎 — 从对话中提取用户行为模式

观察维度：
  comm    — 沟通风格（简洁/详细、中文/英文、正式/随意）
  pref    — 偏好（喜欢的工具、常用的操作）
  rhythm  — 使用节奏（活跃时段、任务频率）
  persona — 角色倾向（技术/产品/设计）

每条观察有 strength 字段：
  - 正反馈（用户确认）→ strength += 1
  - 负反馈（用户纠正）→ strength -= 1
  - strength <= 0 → 自动删除
"""

import re
import time
from typing import Any

import memory_store as mem

# 负反馈关键词
NEGATIVE_PATTERNS = [
    r"不是这样", r"不对", r"错了", r"太啰嗦", r"太长了", r"太短了",
    r"不要", r"别这样", r"换个方式", r"重新来", r"不对劲",
    r"不好", r"不行", r"不太对", r"不满意", r"不喜欢",
    r"not like this", r"wrong", r"too long", r"too short",
    r"don't", r"stop", r"redo", r"try again",
]

# 正反馈关键词
POSITIVE_PATTERNS = [
    r"好的", r"对的", r"没错", r"就是这样", r"很好", r"完美",
    r"不错", r"可以", r"行", r"嗯", r"ok", r"yes",
    r"good", r"perfect", r"right", r"exactly", r"great",
]

# 观察维度提取规则
DIMENSION_RULES = {
    "comm": {
        "keywords": ["简洁", "详细", "中文", "英文", "正式", "随意", "简短", "长一点"],
        "patterns": [
            (r"(简短|简洁|简单)", "concise"),
            (r"(详细|具体|展开)", "detailed"),
            (r"(中文|汉语)", "chinese"),
            (r"(英文|英语)", "english"),
        ],
    },
    "pref": {
        "keywords": ["喜欢", "常用", "偏好", "习惯", "总是", "每次"],
        "patterns": [
            (r"(喜欢|偏好|习惯).{0,10}(用|使用)", "prefer_tool"),
            (r"(总是|每次|经常).{0,10}(先|首先)", "prefer_order"),
        ],
    },
    "rhythm": {
        "keywords": ["早上", "晚上", "下午", "凌晨", "白天", "深夜"],
        "patterns": [
            (r"(早上|上午|清晨)", "morning"),
            (r"(下午|午后)", "afternoon"),
            (r"(晚上|夜晚|晚间)", "evening"),
            (r"(凌晨|深夜|夜里)", "late_night"),
        ],
    },
    "persona": {
        "keywords": ["技术", "产品", "设计", "架构", "前端", "后端"],
        "patterns": [
            (r"(技术|工程|开发|编程)", "technical"),
            (r"(产品|需求|用户)", "product"),
            (r"(设计|UI|UX|界面)", "design"),
        ],
    },
}


def _detect_feedback(text: str) -> str | None:
    """
    检测用户反馈类型：positive / negative / None

    改进：上下文感知，减少误判
    - 短消息（< 15 字）+ 反馈词在开头 → 高置信度反馈
    - 长消息中的反馈词可能是其他语境（如"这个不行，但是..."）
    - 包含否定词的"正反馈"应判为负反馈（如"不好"、"不行"）
    """
    text_stripped = text.strip()
    text_lower = text_stripped.lower()
    msg_len = len(text_stripped)

    # 否定修饰检测：如果"正反馈词"前面有否定词，应判为负反馈
    negation_prefixes = ["不", "没", "别", "不要", "不是", "不行", "不好", "不太", "not", "don't", "isn't", "doesn't"]

    # 先检测负反馈
    for pattern in NEGATIVE_PATTERNS:
        if re.search(pattern, text_lower):
            return "negative"

    # 检测正反馈（带上下文过滤）
    for pattern in POSITIVE_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            matched_text = match.group()
            match_pos = match.start()

            # 检查是否有否定修饰
            prefix = text_lower[max(0, match_pos - 5):match_pos]
            if any(neg in prefix for neg in negation_prefixes):
                return "negative"  # "不好" → 负反馈

            # 短消息（< 10 字）+ 反馈词在前半部分 → 高置信度正反馈
            if msg_len < 10 and match_pos < msg_len // 2:
                return "positive"

            # 长消息中独立出现的正反馈词（前后有标点或空格）
            if msg_len >= 15:
                # 检查是否是独立的词（前后有标点/空格/开头/结尾）
                before = text_lower[match_pos - 1] if match_pos > 0 else " "
                after = text_lower[match_pos + len(matched_text)] if match_pos + len(matched_text) < msg_len else " "
                if before in " ,;.，。；！!?？\n\t" and after in " ,;.，。；！!?？\n\t":
                    return "positive"

            # 其他情况：不判定为反馈（避免误判）
            continue

    return None


def _extract_dimension(text: str) -> tuple[str | None, str | None]:
    """从文本中提取观察维度和值"""
    for dim, rules in DIMENSION_RULES.items():
        for pattern, value in rules["patterns"]:
            if re.search(pattern, text):
                return dim, value
    return None, None


def _find_related_observations(text: str) -> list[dict]:
    """查找与当前文本相关的观察"""
    # 首先搜索 observation 类型的条目
    results = mem.search(text, top_k=20)
    observations = [r for r in results if r.get("type") == "observation"]

    # 如果没找到，返回所有观察
    if not observations:
        observations = get_observations()

    return observations


def update_observations(conversation: str) -> dict:
    """
    从对话中更新观察。

    流程：
    1. 检测是否有正/负反馈
    2. 如果有负反馈，查找相关观察并降低 strength
    3. 如果有正反馈，查找相关观察并提升 strength
    4. 提取新的观察并保存
    """
    feedback = _detect_feedback(conversation)
    dimension, value = _extract_dimension(conversation)

    actions = []

    # 处理负反馈
    if feedback == "negative":
        related = _find_related_observations(conversation)
        for obs in related:
            obs_id = obs.get("id")
            old_strength = obs.get("strength", 3)
            new_strength = old_strength - 1

            if new_strength <= 0:
                # strength 降到 0，删除观察
                mem.delete(obs_id)
                actions.append({
                    "action": "deleted",
                    "id": obs_id,
                    "reason": "strength reached 0",
                })
            else:
                # 更新 strength
                _update_strength(obs_id, new_strength)
                actions.append({
                    "action": "decreased",
                    "id": obs_id,
                    "old_strength": old_strength,
                    "new_strength": new_strength,
                })

    # 处理正反馈
    elif feedback == "positive":
        related = _find_related_observations(conversation)
        for obs in related:
            obs_id = obs.get("id")
            old_strength = obs.get("strength", 3)
            new_strength = min(old_strength + 1, 10)  # 上限 10

            _update_strength(obs_id, new_strength)
            actions.append({
                "action": "increased",
                "id": obs_id,
                "old_strength": old_strength,
                "new_strength": new_strength,
            })

    # 提取新观察
    if dimension and value:
        # 检查是否已有相同观察
        existing = _find_related_observations(f"{dimension}:{value}")
        if not existing:
            obs_id = _save_observation(dimension, value, conversation)
            actions.append({
                "action": "created",
                "id": obs_id,
                "dimension": dimension,
                "value": value,
            })

    return {
        "feedback": feedback,
        "dimension": dimension,
        "value": value,
        "actions": actions,
    }


def _save_observation(dimension: str, value: str, context: str) -> str:
    """保存一条观察"""
    return mem.save_observation(
        dimension=dimension,
        value=value,
        context=context,
        strength=3,
    )


def _update_strength(obs_id: str, new_strength: int):
    """更新观察的 strength"""
    entry = mem.get(obs_id)
    if not entry:
        return

    entry["strength"] = new_strength
    entry["updated_at"] = time.time()

    import json
    import os
    path = os.path.join(mem.ENTRIES_DIR, f"{obs_id}.json")
    if os.path.isfile(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)


def get_observations(dimension: str | None = None, min_strength: int = 1) -> list[dict]:
    """获取观察列表"""
    results = mem.search("observation", top_k=50)
    observations = [r for r in results if r.get("type") == "observation"]

    if dimension:
        observations = [o for o in observations if dimension in o.get("tags", [])]

    observations = [o for o in observations if o.get("strength", 0) >= min_strength]

    return observations


def cleanup_weak_observations(min_strength: int = 1) -> dict:
    """清理 strength 过低的观察"""
    observations = get_observations(min_strength=0)
    deleted = 0

    for obs in observations:
        if obs.get("strength", 0) < min_strength:
            mem.delete(obs.get("id"))
            deleted += 1

    return {"deleted": deleted, "remaining": len(observations) - deleted}
