"""
适应引擎 — 根据观察调整 agent 行为参数

行为参数：
  response_style  — 回应风格（concise/detailed）
  language        — 语言偏好（chinese/english）
  tech_depth      — 技术深度（shallow/medium/deep）
  formality       — 正式程度（casual/normal/formal）

从 observation_engine 读取观察，计算加权平均得到当前行为参数。
strength 越高的观察影响越大。
"""

import time
from typing import Any

import observation_engine as obs_engine

# 默认行为参数
DEFAULT_PARAMS = {
    "response_style": "normal",    # concise / normal / detailed
    "language": "chinese",         # chinese / english
    "tech_depth": "medium",        # shallow / medium / deep
    "formality": "normal",         # casual / normal / formal
}

# 观察维度到行为参数的映射
DIMENSION_TO_PARAM = {
    "comm:concise": ("response_style", "concise", 2),
    "comm:detailed": ("response_style", "detailed", 2),
    "comm:chinese": ("language", "chinese", 2),
    "comm:english": ("language", "english", 2),
    "comm:formal": ("formality", "formal", 1),
    "comm:casual": ("formality", "casual", 1),
    "persona:technical": ("tech_depth", "deep", 1),
    "persona:product": ("tech_depth", "shallow", 1),
}


def get_behavior_params() -> dict:
    """
    根据当前观察计算行为参数。

    遍历所有观察，按 strength 加权投票决定每个参数。
    """
    observations = obs_engine.get_observations(min_strength=1)

    if not observations:
        return DEFAULT_PARAMS.copy()

    # 统计每个参数值的加权票数
    votes: dict[str, dict[str, float]] = {
        "response_style": {},
        "language": {},
        "tech_depth": {},
        "formality": {},
    }

    for obs in observations:
        dimension = obs.get("dimension", "")
        value = obs.get("observation", "")
        strength = obs.get("strength", 1)
        key = f"{dimension}:{value}"

        if key in DIMENSION_TO_PARAM:
            param_name, param_value, weight = DIMENSION_TO_PARAM[key]
            if param_value not in votes[param_name]:
                votes[param_name][param_value] = 0
            votes[param_name][param_value] += strength * weight

    # 选择票数最高的值
    params = DEFAULT_PARAMS.copy()
    for param_name, value_votes in votes.items():
        if value_votes:
            best_value = max(value_votes, key=value_votes.get)
            params[param_name] = best_value

    return params


def get_adapted_system_prompt(base_prompt: str) -> str:
    """
    根据行为参数调整系统提示。

    在基础提示后追加适应性指令。
    """
    params = get_behavior_params()

    adaptations = []

    if params["response_style"] == "concise":
        adaptations.append("用户偏好简洁回复，避免冗长解释。")
    elif params["response_style"] == "detailed":
        adaptations.append("用户偏好详细回复，给出完整解释和示例。")

    if params["language"] == "chinese":
        adaptations.append("使用中文回复。")
    elif params["language"] == "english":
        adaptations.append("Use English to respond.")

    if params["tech_depth"] == "deep":
        adaptations.append("用户有较强技术背景，可以使用专业术语。")
    elif params["tech_depth"] == "shallow":
        adaptations.append("用户可能非技术背景，避免过多技术细节。")

    if adaptations:
        return base_prompt + "\n\nUSER PREFERENCES:\n" + "\n".join(adaptations)

    return base_prompt


def record_feedback(user_message: str, feedback_type: str) -> dict:
    """
    记录用户反馈。

    参数：
      user_message: 用户消息
      feedback_type: "positive" / "negative"

    返回：更新的观察列表
    """
    observations = obs_engine.get_observations(min_strength=1)
    actions = []

    for obs in observations:
        obs_id = obs.get("id")
        old_strength = obs.get("strength", 3)

        if feedback_type == "negative":
            new_strength = old_strength - 1
            if new_strength <= 0:
                from memory_store import delete
                delete(obs_id)
                actions.append({"action": "deleted", "id": obs_id})
            else:
                obs_engine._update_strength(obs_id, new_strength)
                actions.append({
                    "action": "decreased",
                    "id": obs_id,
                    "new_strength": new_strength,
                })
        elif feedback_type == "positive":
            new_strength = min(old_strength + 1, 10)
            obs_engine._update_strength(obs_id, new_strength)
            actions.append({
                "action": "increased",
                "id": obs_id,
                "new_strength": new_strength,
            })

    return {"feedback_type": feedback_type, "actions": actions}


def get_adaptation_summary() -> dict:
    """获取当前适应状态摘要"""
    params = get_behavior_params()
    observations = obs_engine.get_observations(min_strength=1)

    obs_by_dimension = {}
    for obs in observations:
        dim = obs.get("dimension", "unknown")
        if dim not in obs_by_dimension:
            obs_by_dimension[dim] = []
        obs_by_dimension[dim].append({
            "value": obs.get("observation", ""),
            "strength": obs.get("strength", 0),
        })

    return {
        "params": params,
        "observation_count": len(observations),
        "observations_by_dimension": obs_by_dimension,
    }
