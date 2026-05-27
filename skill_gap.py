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


# ========== 记录失败 ==========

def record_failure(
    user_input: str,
    error: str,
    context: str = "",
    failed_action: str = "",
    source: str = "intent",
):
    """
    记录一次失败事件。

    source: "intent" | "agent" | "skill_match" | "validation"
    """
    gaps = _load_json(GAP_LOG_FILE, {"failures": []})

    entry = {
        "id": f"{int(time.time()*1000)}_{len(gaps['failures'])}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_input": user_input[:500],
        "error": str(error)[:500],
        "context": context[:500],
        "failed_action": failed_action,
        "source": source,
        "analyzed": False,
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
    分析所有失败记录，识别技能缺口。

    返回：
      {
        "top_gaps": [{"domain": "xxx", "count": N, "examples": [...]}],
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

    for f in failures:
        text = f.get("user_input", "") + " " + f.get("error", "") + " " + f.get("failed_action", "")
        domains = _extract_keywords(text)
        for d in domains:
            domain_counts[d] = domain_counts.get(d, 0) + 1
            if d not in domain_examples:
                domain_examples[d] = []
            if len(domain_examples[d]) < 3:
                domain_examples[d].append(f.get("user_input", "")[:100])

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

    # 用需求计数补充推荐
    top_keywords = list(demand.get("keywords", {}).keys())[:10]

    return {
        "top_gaps": top_gaps_list,
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
