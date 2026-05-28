"""
统一 LLM 调用客户端 — 支持 fallback 降级

特性：
  - 主模型失败时自动切换备用模型
  - 支持同步调用（_call_llm）和流式调用（stream）
  - 记录每个模型的成功/失败状态，优先使用可用模型
  - 所有模型均不可用时返回 None（不抛异常）
"""

import time
from typing import AsyncGenerator

import httpx
from openai import OpenAI

import config

# 模型可用性缓存：{model_name: {"available": bool, "last_check": timestamp, "fail_count": int}}
_model_health: dict[str, dict] = {}


def _get_model_chain() -> list[str]:
    """返回模型调用优先级列表：主模型 + 备用模型"""
    chain = [config.MODEL]
    for m in config.MODEL_FALLBACKS:
        if m not in chain:
            chain.append(m)
    return chain


def _pick_model() -> str | None:
    """选择当前最可能可用的模型"""
    chain = _get_model_chain()

    # 优先选已知可用且最近成功的
    for model in chain:
        health = _model_health.get(model)
        if health and health["available"] and health["fail_count"] == 0:
            return model

    # 其次选未测试过的（乐观策略）
    for model in chain:
        if model not in _model_health:
            return model

    # 最后选失败次数最少的
    best = None
    best_fail = float("inf")
    for model in chain:
        health = _model_health.get(model, {})
        fc = health.get("fail_count", 0)
        if fc < best_fail:
            best_fail = fc
            best = model

    return best


def _mark_success(model: str):
    """标记模型调用成功"""
    _model_health[model] = {"available": True, "last_check": time.time(), "fail_count": 0}


def _mark_failure(model: str):
    """标记模型调用失败"""
    prev = _model_health.get(model, {"available": True, "fail_count": 0})
    _model_health[model] = {
        "available": False,
        "last_check": time.time(),
        "fail_count": prev.get("fail_count", 0) + 1,
    }


def reset_health():
    """重置所有模型的健康状态（用于手动恢复）"""
    _model_health.clear()


def get_health_status() -> dict:
    """获取所有模型的健康状态"""
    return {
        "chain": _get_model_chain(),
        "health": dict(_model_health),
        "current_pick": _pick_model(),
    }


def call_llm(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.1,
    model: str | None = None,
    timeout: int | None = None,
) -> str | None:
    """
    同步调用 LLM，支持自动 fallback。

    返回模型响应文本，所有模型均失败时返回 None。
    """
    chain = _get_model_chain() if model is None else [model]
    timeout = timeout or config.TOOL_TIMEOUT

    for model_name in chain:
        try:
            client = OpenAI(
                api_key=config.API_KEY,
                base_url=config.API_BASE_URL,
                http_client=httpx.Client(trust_env=False),
            )
            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                timeout=timeout,
            )
            content = resp.choices[0].message.content
            if content:
                _mark_success(model_name)
                return content
            # 空响应视为失败
            _mark_failure(model_name)
        except Exception as e:
            _mark_failure(model_name)
            continue

    return None


async def call_llm_stream(
    messages: list[dict],
    model: str | None = None,
    tools: list | None = None,
    timeout: int | None = None,
) -> AsyncGenerator[dict, None]:
    """
    流式调用 LLM，支持自动 fallback。

    yield 每个 chunk 的 delta，最终 yield {"done": True, "model": model_name}
    如果所有模型失败，yield {"done": False, "error": "..."}
    """
    chain = _get_model_chain() if model is None else [model]
    timeout = timeout or config.TOOL_TIMEOUT

    for model_name in chain:
        try:
            client = OpenAI(
                api_key=config.API_KEY,
                base_url=config.API_BASE_URL,
                http_client=httpx.Client(trust_env=False),
            )
            kwargs = {
                "model": model_name,
                "messages": messages,
                "stream": True,
                "timeout": timeout,
            }
            if tools:
                kwargs["tools"] = tools

            stream = client.chat.completions.create(**kwargs)

            yielded_any = False
            for chunk in stream:
                if chunk.choices:
                    yield {"chunk": chunk.choices[0], "model": model_name}
                    yielded_any = True

            if yielded_any:
                _mark_success(model_name)
                yield {"done": True, "model": model_name}
                return
            else:
                _mark_failure(model_name)
        except Exception:
            _mark_failure(model_name)
            continue

    yield {"done": False, "error": "所有模型均不可用"}


def call_llm_with_fallback(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.1,
) -> tuple[str | None, str]:
    """
    同步调用，返回 (response, model_name)。
    方便调用方知道用的是哪个模型。
    """
    chain = _get_model_chain()

    for model_name in chain:
        try:
            client = OpenAI(
                api_key=config.API_KEY,
                base_url=config.API_BASE_URL,
                http_client=httpx.Client(trust_env=False),
            )
            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                timeout=config.TOOL_TIMEOUT,
            )
            content = resp.choices[0].message.content
            if content:
                _mark_success(model_name)
                return content, model_name
            _mark_failure(model_name)
        except Exception:
            _mark_failure(model_name)
            continue

    return None, ""
