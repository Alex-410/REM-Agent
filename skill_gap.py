"""
技能缺口自动识别 — P5

机制：
  1. 记录失败的任务/执行/请求
  2. 分析失败模式，识别缺失技能
  3. 用 LLM 推荐需要学习的技能
  4. 与 self_learning 集成，自动触发学习

数据来源：
  - intent_engine 执行失败
  - agent 工具调用失败
  - 用户请求无法匹配到技能
  - 技能验证失败
"""

import json
import os
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GAP_LOG_FILE = os.path.join(BASE_DIR, ".memory", "skill_gaps.json")
DEMAND_FILE = os.path.join(BASE_DIR, ".memory", "skill_demand.json")

# 失败记录过期时间（7天）
EXPIRY_SECONDS = 7 * 24 * 3600


def _ensure_dir():
    os.makedirs(os.path.dirname(GAP_LOG_FILE), exist_ok=True)


def _load_json(path: str, default=None):
    if default is None:
        default = {}
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: str, data):
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ========== 根因分析 ==========

# 根因分类
ROOT_CAUSE_CATEGORIES = {
    "tool_missing": "工具不存在或未注册",
    "param_error": "参数错误（类型、格式、缺失）",
    "permission": "权限不足（文件访问、API 权限）",
    "env_issue": "环境问题（依赖缺失、服务不可用）",
    "logic_error": "逻辑错误（方案本身有误）",
    "knowledge_gap": "知识盲区（不知道怎么做）",
    "network": "网络问题（超时、连接失败）",
    "timeout": "执行超时",
    "unknown": "未知原因",
}

# 快速根因推断（基于错误关键词，不需要 LLM）
_ERROR_PATTERNS = {
    "tool_missing": ["not found", "unknown tool", "no such tool", "未找到工具"],
    "param_error": ["invalid argument", "type error", "missing required", "参数错误", "validation error"],
    "permission": ["permission denied", "access denied", "forbidden", "权限", "403"],
    "env_issue": ["no module named", "module not found", "command not found", "not installed", "依赖", "import error"],
    "network": ["connection error", "timeout", "network", "dns", "连接", "超时", "http error"],
    "timeout": ["timeout", "timed out", "超时"],
}


def _quick_classify(error: str) -> str:
    """快速根因推断（基于关键词匹配）"""
    error_lower = error.lower()
    for cause, patterns in _ERROR_PATTERNS.items():
        for pattern in patterns:
            if pattern in error_lower:
                return cause
    return "unknown"


def _llm_classify_root_cause(user_input: str, error: str, failed_action: str, context: str) -> dict:
    """
    用 LLM 深度分析失败根因。
    只在快速分类返回 "unknown" 时调用，节省 API 调用。
    """
    prompt = f"""分析以下执行失败的根因，返回 JSON。

用户指令：{user_input[:200]}
失败工具：{failed_action}
错误信息：{error[:300]}
上下文：{context[:200]}

根因分类（选一个）：
- tool_missing: 工具不存在或未注册
- param_error: 参数错误
- permission: 权限不足
- env_issue: 环境问题（依赖缺失等）
- logic_error: 方案本身有误
- knowledge_gap: 不知道怎么做
- network: 网络问题
- timeout: 超时
- unknown: 未知

返回 JSON：{{"root_cause": "分类", "detail": "一句话解释为什么", "fix_suggestion": "建议怎么修复"}}
只输出 JSON。"""

    try:
        from llm_client import call_llm
        result = call_llm("你是一个执行失败根因分析器。", prompt, temperature=0.1)
        if result:
            import json as _json
            text = result.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                if len(lines) >= 3:
                    text = "\n".join(lines[1:-1])
            return _json.loads(text)
    except Exception:
        pass

    return {"root_cause": "unknown", "detail": "LLM 分析失败", "fix_suggestion": ""}


# ========== 记录失败 ==========

def record_failure(
    user_input: str,
    error: str,
    context: str = "",
    failed_action: str = "",
    source: str = "intent",
):
    """
    记录一次失败事件，自动进行根因分析。

    source: "intent" | "agent" | "skill_match" | "validation"
    """
    gaps = _load_json(GAP_LOG_FILE, {"failures": []})

    # 快速根因推断
    root_cause = _quick_classify(error)

    # 如果快速分类为 unknown，尝试 LLM 深度分析
    cause_detail = ""
    fix_suggestion = ""
    if root_cause == "unknown" and len(error) > 10:
        llm_result = _llm_classify_root_cause(user_input, error, failed_action, context)
        root_cause = llm_result.get("root_cause", "unknown")
        cause_detail = llm_result.get("detail", "")
        fix_suggestion = llm_result.get("fix_suggestion", "")

    entry = {
        "id": f"{int(time.time()*1000)}_{len(gaps['failures'])}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_input": user_input[:500],
        "error": str(error)[:500],
        "context": context[:500],
        "failed_action": failed_action,
        "source": source,
        "root_cause": root_cause,
        "cause_detail": cause_detail,
        "fix_suggestion": fix_suggestion,
        "analyzed": root_cause != "unknown",
    }
    gaps["failures"].append(entry)

    # 清理过期记录
    now = time.time()
    gaps["failures"] = [
        f for f in gaps["failures"]
        if now - _parse_timestamp(f.get("timestamp", "")) < EXPIRY_SECONDS
    ]

    _save_json(GAP_LOG_FILE, gaps)

    # 更新需求计数
    _update_demand(user_input, error, failed_action)

    return entry["id"]


def _parse_timestamp(ts: str) -> float:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except (ValueError, AttributeError):
        return 0.0


def _update_demand(user_input: str, error: str, action: str):
    """更新技能需求计数"""
    demand = _load_json(DEMAND_FILE, {"skills": {}, "keywords": {}})

    # 提取关键词
    keywords = _extract_keywords(user_input + " " + error + " " + action)

    for kw in keywords:
        if kw in demand["keywords"]:
            demand["keywords"][kw] += 1
        else:
            demand["keywords"][kw] = 1

    # 按频次排序，保留 top 50
    demand["keywords"] = dict(
        sorted(demand["keywords"].items(), key=lambda x: -x[1])[:50]
    )

    demand["last_updated"] = datetime.now(timezone.utc).isoformat()
    _save_json(DEMAND_FILE, demand)


def _extract_keywords(text: str) -> list[str]:
    """从文本中提取技能相关关键词"""
    text_lower = text.lower()

    # 技能领域关键词映射
    domain_keywords = {
        "web": ["web", "html", "css", "javascript", "react", "vue", "frontend"],
        "scraping": ["scraping", "crawl", "spider", "extract", "parse html"],
        "api": ["api", "rest", "graphql", "endpoint", "http request"],
        "database": ["database", "sql", "mysql", "postgres", "mongodb", "redis"],
        "image": ["image", "photo", "picture", "draw", "paint", "canvas", "pillow"],
        "data": ["data", "pandas", "numpy", "csv", "excel", "analysis", "chart"],
        "automation": ["automat", "script", "batch", "cron", "schedule"],
        "testing": ["test", "pytest", "unittest", "mock", "coverage"],
        "docker": ["docker", "container", "kubernetes", "deploy"],
        "git": ["git", "commit", "branch", "merge", "rebase"],
        "file": ["file", "folder", "directory", "path", "rename", "copy"],
        "network": ["network", "socket", "tcp", "udp", "proxy"],
        "security": ["security", "encrypt", "auth", "token", "password"],
        "ai": ["ai", "ml", "model", "train", "predict", "llm", "gpt"],
        "desktop": ["desktop", "gui", "window", "mouse", "keyboard", "click"],
        "wechat": ["wechat", "weixin", "微信"],
        "pdf": ["pdf", "document", "report"],
        "email": ["email", "smtp", "imap", "mail"],
        "audio": ["audio", "sound", "music", "mp3", "wav"],
        "video": ["video", "mp4", "ffmpeg", "youtube"],
    }

    found = []
    for domain, keywords in domain_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                found.append(domain)
                break

    return found


# ========== 分析缺口 ==========

def analyze_gaps() -> dict:
    """
    分析所有失败记录，识别技能缺口和根因分布。

    返回：
      {
        "top_gaps": [{"domain": "xxx", "count": N, "examples": [...]}],
        "root_cause_distribution": {"tool_missing": N, "env_issue": N, ...},
        "total_failures": N,
        "unanalyzed": N,
        "recommendations": ["topic1", "topic2", ...]
      }
    """
    gaps = _load_json(GAP_LOG_FILE, {"failures": []})
    demand = _load_json(DEMAND_FILE, {"skills": {}, "keywords": {}})

    failures = gaps.get("failures", [])
    unanalyzed = [f for f in failures if not f.get("analyzed")]

    # 按领域聚合失败
    domain_counts = {}
    domain_examples = {}

    # 按根因聚合
    root_cause_counts = {}

    for f in failures:
        text = f.get("user_input", "") + " " + f.get("error", "") + " " + f.get("failed_action", "")
        domains = _extract_keywords(text)
        for d in domains:
            domain_counts[d] = domain_counts.get(d, 0) + 1
            if d not in domain_examples:
                domain_examples[d] = []
            if len(domain_examples[d]) < 3:
                domain_examples[d].append(f.get("user_input", "")[:100])

        # 统计根因
        rc = f.get("root_cause", "unknown")
        root_cause_counts[rc] = root_cause_counts.get(rc, 0) + 1

    # 排序
    top_gaps = sorted(domain_counts.items(), key=lambda x: -x[1])
    top_gaps_list = [
        {
            "domain": domain,
            "count": count,
            "examples": domain_examples.get(domain, []),
        }
        for domain, count in top_gaps[:10]
    ]

    # 根因分布
    root_cause_distribution = dict(
        sorted(root_cause_counts.items(), key=lambda x: -x[1])
    )

    # 用需求计数补充推荐
    top_keywords = list(demand.get("keywords", {}).keys())[:10]

    return {
        "top_gaps": top_gaps_list,
        "root_cause_distribution": root_cause_distribution,
        "total_failures": len(failures),
        "unanalyzed": len(unanalyzed),
        "top_demand_keywords": top_keywords,
        "recommendations": _generate_recommendations(top_gaps_list, top_keywords),
    }


def _generate_recommendations(gaps: list[dict], keywords: list[str]) -> list[str]:
    """根据缺口和需求生成学习推荐"""
    recommendations = []

    # 从缺口提取
    for gap in gaps[:5]:
        domain = gap["domain"]
        if gap["count"] >= 2:  # 至少出现 2 次才推荐
            recommendations.append(domain)

    # 从关键词补充
    for kw in keywords:
        if kw not in recommendations:
            recommendations.append(kw)

    return recommendations[:8]


def recommend_skills_for_gaps() -> list[str]:
    """
    推荐应该学习的技能主题。
    供 self_learning._identify_gaps() 调用。
    """
    analysis = analyze_gaps()
    return analysis.get("recommendations", [])


def mark_analyzed(failure_ids: list[str] | None = None):
    """标记失败记录为已分析"""
    gaps = _load_json(GAP_LOG_FILE, {"failures": []})
    for f in gaps["failures"]:
        if failure_ids is None or f.get("id") in failure_ids:
            f["analyzed"] = True
    _save_json(GAP_LOG_FILE, gaps)


# ========== 无匹配技能记录 ==========

def record_unmatched_request(user_input: str, available_skills: list[str]):
    """记录用户请求但没有匹配到技能的情况"""
    record_failure(
        user_input=user_input,
        error="no_matching_skill",
        context=f"Available skills: {', '.join(available_skills[:10])}",
        failed_action="skill_match",
        source="skill_match",
    )


# ========== 统计 API ==========

def get_gap_stats() -> dict:
    """获取技能缺口统计"""
    gaps = _load_json(GAP_LOG_FILE, {"failures": []})
    demand = _load_json(DEMAND_FILE, {"skills": {}, "keywords": {}})
    analysis = analyze_gaps()

    return {
        "total_failures": len(gaps.get("failures", [])),
        "unanalyzed": analysis["unanalyzed"],
        "top_gaps": analysis["top_gaps"][:5],
        "top_demand": list(demand.get("keywords", {}).keys())[:10],
        "recommendations": analysis["recommendations"],
    }
