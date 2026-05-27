"""
持久化记忆系统 — v2: 向量检索 + 关键词回退

存什么：用户指令 → 解析结果 → 执行方案 → 执行结果 → 向量
怎么存：JSON 文件 + NumPy 向量文件，按时间 + 语义索引
怎么学：新的指令→方案映射自动写入，下次语义匹配命中

文件结构：
  .memory/
    index.json        # 索引：关键词 → [entry_id]
    entries/
      {id}.json       # 单条完整记录
      {id}.npy        # 该条记录的 embedding 向量

检索策略：
  1. 向量 + 关键词 RRF 混合搜索
  2. Ollama 不可用时回退到纯关键词匹配
"""

import json
import os
import time
import hashlib
import re
import warnings
from typing import Any

warnings.filterwarnings("ignore", category=UserWarning)

import config

MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".memory")
ENTRIES_DIR = os.path.join(MEMORY_DIR, "entries")
INDEX_FILE = os.path.join(MEMORY_DIR, "index.json")

MAX_ENTRIES = 200

# Ollama 配置（从 config.py 读取）
OLLAMA_BASE = config.OLLAMA_HOST
EMBED_MODEL = config.EMBED_MODEL

# ========== Embedding 客户端 ==========

_EMBED_CACHE: dict[str, list[float]] = {}


def _ollama_embed(texts: list[str]) -> list[list[float]] | None:
    """调用 Ollama embedding API，返回 None 表示失败"""
    uncached = [t for t in texts if t not in _EMBED_CACHE]
    if uncached:
        try:
            import urllib.request
            import json as _json

            payload = _json.dumps({"model": EMBED_MODEL, "input": uncached}).encode()
            req = urllib.request.Request(
                f"{OLLAMA_BASE}/api/embed",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            # 绕过 HTTP_PROXY（Ollama 是本地服务，不走代理）
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            resp = opener.open(req, timeout=30)
            data = _json.loads(resp.read().decode())
            for t, vec in zip(uncached, data.get("embeddings", [])):
                _EMBED_CACHE[t] = vec
        except Exception:
            return None

    return [_EMBED_CACHE[t] for t in texts]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ========== 持久化基础 ==========


def _ensure_dirs():
    os.makedirs(ENTRIES_DIR, exist_ok=True)


def _load_index() -> dict:
    if not os.path.isfile(INDEX_FILE):
        return {"keywords": {}, "entries": []}
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"keywords": {}, "entries": []}


def _save_index(index: dict):
    _ensure_dirs()
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _extract_keywords(text: str) -> list[str]:
    """从文本中提取关键词（分词 + 去停用词）"""
    text = text.lower()
    words = set()
    for m in re.finditer(r"[一-鿿]{2,4}", text):
        words.add(m.group())
    for m in re.finditer(r"[a-z]{3,}", text):
        words.add(m.group())
    stopwords = {
        "一个", "什么", "怎么", "这个", "那个", "可以", "想要", "需要",
        "the", "and", "for", "are", "but", "not", "you", "all", "any",
        "can", "has", "had", "was", "get", "how", "why", "what",
    }
    return [w for w in words if w not in stopwords]


def _entry_path(entry_id: str) -> str:
    return os.path.join(ENTRIES_DIR, f"{entry_id}.json")


def _vector_path(entry_id: str) -> str:
    return os.path.join(ENTRIES_DIR, f"{entry_id}.npy")


def _compute_id(user_input: str) -> str:
    return hashlib.sha256(user_input.strip().lower().encode()).hexdigest()[:16]


# ========== 向量存储 ==========


def _save_vector(entry_id: str, vector: list[float]):
    """保存向量到 .npy 文件（用纯 JSON 避免 numpy 依赖）"""
    path = _vector_path(entry_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(vector, f)


def _load_vector(entry_id: str) -> list[float] | None:
    """加载向量"""
    path = _vector_path(entry_id)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# ========== 核心 API ==========


def save(user_input: str, plan: list, result: str, tags: list[str] | None = None, step_results: list[dict] | None = None, entry_type: str = "success", extra: dict | None = None) -> str:
    """
    保存一条记忆。

    参数：
      entry_type: "success" / "failure" / "knowledge" / "session" / "observation"
      extra: 类型特定的额外字段（如 observation 的 strength/dimension）
    """
    _ensure_dirs()
    entry_id = _compute_id(user_input)
    keywords = _extract_keywords(user_input)
    if tags:
        keywords.extend(tags)
    keywords = list(set(keywords))

    # 从 plan 和 step_results 中提取关键词（工具名、动作等）
    for step in (plan or []):
        action = step.get("action", "")
        if action:
            keywords.extend(_extract_keywords(action))
        desc = step.get("description", "")
        if desc:
            keywords.extend(_extract_keywords(desc))
    keywords = list(set(keywords))

    now = time.time()
    entry = {
        "id": entry_id,
        "type": entry_type,
        "user_input": user_input,
        "plan": plan,
        "step_results": step_results or [],
        "result": result,
        "keywords": keywords,
        "created_at": now,
        "updated_at": now,
        "hit_count": 0,
        "has_vector": False,
    }

    # observation 类型特有字段
    if entry_type == "observation":
        entry["strength"] = extra.get("strength", 3) if extra else 3
        entry["dimension"] = extra.get("dimension", "") if extra else ""
        entry["observation"] = extra.get("observation", "") if extra else ""

    # 其他类型特有字段
    if extra:
        entry.update(extra)

    with open(_entry_path(entry_id), "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)

    # 异步生成并保存向量
    _sync_vector_async(entry_id, user_input)

    # 更新索引
    index = _load_index()
    for kw in keywords:
        if kw not in index["keywords"]:
            index["keywords"][kw] = []
        if entry_id not in index["keywords"][kw]:
            index["keywords"][kw].append(entry_id)

    if entry_id not in index["entries"]:
        index["entries"].insert(0, entry_id)
    else:
        index["entries"].remove(entry_id)
        index["entries"].insert(0, entry_id)

    while len(index["entries"]) > MAX_ENTRIES:
        old_id = index["entries"].pop()
        old_path = _entry_path(old_id)
        if os.path.isfile(old_path):
            os.remove(old_path)
        vp = _vector_path(old_id)
        if os.path.isfile(vp):
            os.remove(vp)

    _save_index(index)
    return entry_id


def save_observation(dimension: str, value: str, context: str, strength: int = 3) -> str:
    """保存一条观察"""
    return save(
        user_input=f"{dimension}:{value}",
        plan=[],
        result=context[:200],
        tags=["observation", dimension],
        step_results=[],
        entry_type="observation",
        extra={
            "strength": strength,
            "dimension": dimension,
            "observation": value,
        },
    )


def _sync_vector_async(entry_id: str, text: str):
    """同步生成向量（实际调用很快，直接同步执行）"""
    vecs = _ollama_embed([text])
    if vecs:
        _save_vector(entry_id, vecs[0])
        # 更新 entry 标记
        entry = _load_entry(entry_id)
        if entry:
            entry["has_vector"] = True
            with open(_entry_path(entry_id), "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)


def _load_entry(entry_id: str) -> dict | None:
    path = _entry_path(entry_id)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def search(query: str, top_k: int = 5) -> list[dict]:
    """
    搜索记忆 — 多级降级策略：

    1. Embedding + RRF hybrid → 返回融合结果
    2. 纯向量搜索（无关键词匹配）
    3. 纯关键词搜索（Ollama 不可用时）
    4. 全部不可用 → 空结果
    """
    index = _load_index()
    if not index["entries"]:
        return []

    query_vec = _ollama_embed([query])

    if query_vec:
        # Level 1 & 2: Hybrid search (RRF 融合)
        hybrid_ids = _hybrid_search(query, query_vec[0], index["entries"], top_k=15)
        results = []
        for eid in hybrid_ids:
            entry = _load_entry(eid)
            if entry:
                vec = _load_vector(eid)
                if vec:
                    entry["_cosine_sim"] = _cosine_similarity(query_vec[0], vec)
                else:
                    entry["_cosine_sim"] = 0.0
                results.append(entry)
        return results[:top_k]

    # Level 3: 纯关键词
    results = _keyword_search(query, index["entries"], top_k)
    for r in results:
        r["_cosine_sim"] = 0.0  # 无向量时的标记
    return results


def _keyword_match_score(query: str, query_keywords: list[str], entry: dict) -> float:
    """
    计算单条记忆的关键词匹配分数。
    """
    entry_input = entry.get("user_input", "")
    query_lower = query.strip().lower()
    entry_lower = entry_input.strip().lower()

    score = 0.0

    # 精确匹配
    if entry_lower == query_lower:
        score += 10.0
    # 包含匹配
    elif query_lower in entry_lower or entry_lower in query_lower:
        score += 5.0

    # 关键词重叠
    entry_keywords = set(entry.get("keywords", []))
    if query_keywords:
        overlap = len(set(query_keywords) & entry_keywords)
        if overlap > 0:
            score += overlap * 2.0

    # 命中次数加成
    hit_count = entry.get("hit_count", 0)
    if hit_count > 0:
        score += min(hit_count * 0.5, 3.0)

    return score


def _rank_in(eid: str, scores: dict[str, float]) -> int:
    """返回 entry_id 在分数字典中的排名（1-based）"""
    sorted_ids = sorted(scores, key=scores.get, reverse=True)
    try:
        return sorted_ids.index(eid) + 1
    except ValueError:
        return len(sorted_ids) + 1


def _hybrid_search(query: str, query_vec: list[float], entry_ids: list[str], top_k: int = 15) -> list[str]:
    """
    向量 + 关键词 RRF 倒数秩融合搜索。

    流程：
      1. 对所有条目计算向量余弦相似度
      2. 对所有条目计算关键词匹配分数
      3. RRF 融合两套排名
      4. 返回 top_k 个 entry_id
    """
    query_keywords = _extract_keywords(query)
    vector_scores: dict[str, float] = {}
    keyword_scores: dict[str, float] = {}

    for entry_id in entry_ids:
        entry = _load_entry(entry_id)
        if not entry:
            continue

        # 向量评分
        vec = _load_vector(entry_id)
        if vec:
            vector_scores[entry_id] = _cosine_similarity(query_vec, vec)

        # 关键词评分
        kw_score = _keyword_match_score(query, query_keywords, entry)
        if kw_score > 0:
            keyword_scores[entry_id] = kw_score

    # RRF 融合
    all_ids = set(vector_scores.keys()) | set(keyword_scores.keys())
    if not all_ids:
        return []

    RRF_K = 60
    fused: dict[str, float] = {}
    for eid in all_ids:
        rank_v = _rank_in(eid, vector_scores) if eid in vector_scores else len(vector_scores) + 1
        rank_k = _rank_in(eid, keyword_scores) if eid in keyword_scores else len(keyword_scores) + 1
        fused[eid] = 1.0 / (RRF_K + rank_v) + 1.0 / (RRF_K + rank_k)

    return sorted(fused, key=fused.get, reverse=True)[:top_k]


def _keyword_search(query: str, entry_ids: list[str], top_k: int) -> list[dict]:
    """纯关键词匹配搜索（Ollama 不可用时的回退）"""
    query_keywords = _extract_keywords(query)
    scored = []
    for entry_id in entry_ids:
        entry = _load_entry(entry_id)
        if not entry:
            continue
        score = _keyword_match_score(query, query_keywords, entry)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: -x[0])
    return [entry for _, entry in scored[:top_k]]


# ========== 兼容旧 API ==========


def get(entry_id: str) -> dict | None:
    return _load_entry(entry_id)


def record_hit(entry_id: str):
    entry = _load_entry(entry_id)
    if not entry:
        return
    entry["hit_count"] = entry.get("hit_count", 0) + 1
    entry["updated_at"] = time.time()
    with open(_entry_path(entry_id), "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)


def delete(entry_id: str):
    path = _entry_path(entry_id)
    if os.path.isfile(path):
        os.remove(path)
    vp = _vector_path(entry_id)
    if os.path.isfile(vp):
        os.remove(vp)
    index = _load_index()
    if entry_id in index["entries"]:
        index["entries"].remove(entry_id)
    for kw, ids in index["keywords"].items():
        if entry_id in ids:
            ids.remove(entry_id)
    _save_index(index)


def stats() -> dict:
    """获取记忆系统状态"""
    index = _load_index()
    total = len(index["entries"])
    vector_count = sum(
        1 for eid in index["entries"]
        if os.path.isfile(_vector_path(eid))
    )

    # 检测 Ollama 是否可用
    ollama_ok = _ollama_embed(["test"]) is not None

    # 检测索引文件是否存在
    index_exists = os.path.isfile(INDEX_FILE)

    return {
        "total_entries": total,
        "vector_count": vector_count,
        "vector_coverage": round(vector_count / total, 2) if total > 0 else 0,
        "total_keywords": len(index.get("keywords", {})),
        "max_entries": MAX_ENTRIES,
        "embedding_model": EMBED_MODEL,
        "ollama_host": OLLAMA_BASE,
        "ollama_available": ollama_ok,
        "index_exists": index_exists,
    }


def rebuild_vectors():
    """为所有还没有向量的条目生成向量"""
    index = _load_index()
    batch = []
    for entry_id in index["entries"]:
        if os.path.isfile(_vector_path(entry_id)):
            continue
        entry = _load_entry(entry_id)
        if entry:
            batch.append((entry_id, entry.get("user_input", "")))

    if not batch:
        return {"rebuild": 0, "message": "所有条目已有向量"}

    texts = [text for _, text in batch]
    vecs = _ollama_embed(texts)
    if not vecs:
        return {"rebuild": 0, "message": "Ollama 不可用"}

    for (eid, _), vec in zip(batch, vecs):
        _save_vector(eid, vec)
        entry = _load_entry(eid)
        if entry:
            entry["has_vector"] = True
            with open(_entry_path(eid), "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)

    return {"rebuild": len(batch), "message": f"已为 {len(batch)} 条生成向量"}
