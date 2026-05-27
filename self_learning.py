"""
自学引擎 — 让 agent 启动后主动学习新技能，而不是等人问了才学

机制：
  1. 启动时扫 GitHub / 技能市场找新技能
  2. 下载并安装到 agent-skills/skills/ 下
  3. 识别自己不会的领域，主动搜索学习并生成技能文件
  4. 所有学到的技能自动注册到 skill_engine，下次直接用

技能清单（skills_manifest.json）：
  记录所有技能的名称、来源、状态、更新时间
  可通过 /api/skills/inventory 查询"你会什么"
"""

import json
import os
import re
import time
import asyncio
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(BASE_DIR, "agent-skills", "skills")
MANIFEST_FILE = os.path.join(BASE_DIR, "skills_manifest.json")
STATE_FILE = os.path.join(BASE_DIR, ".claude", "learning_state.json")
LEARNING_LOG_FILE = os.path.join(BASE_DIR, "learning_log.json")

# 技能来源 — 可扩展
SKILL_SOURCES = [
    {
        "name": "github-agent-skills",
        "type": "github_topic",
        "topic": "agent-skills",
        "enabled": True,
    },
    {
        "name": "github-claude-skills",
        "type": "github_topic",
        "topic": "claude-skills",
        "enabled": True,
    },
]

# 学习间隔（秒）
LEARN_INTERVAL = 3600  # 每 1 小时检查一次（之前是 6 小时）
# 首次启动后快速连扫几次，快速积累技能
INITIAL_BURST_INTERVAL = 300  # 首次启动后每 5 分钟扫一次，连扫 3 轮

# 默认常用技能包（当找不到 GitHub skill 时，用这些兜底）
STARTER_SKILLS = [
    {
        "name": "windows-automation",
        "description": "Windows 桌面自动化：窗口操作、鼠标键盘、OCR 识别、截图。用于控制微信、QQ、浏览器等桌面应用。",
        "phase": "build",
    },
    {
        "name": "web-scraping",
        "description": "从网页提取数据：HTML 解析、API 抓取、动态页面渲染。用于采集信息、监控价格、聚合内容。",
        "phase": "build",
    },
    {
        "name": "image-generation",
        "description": "用 Python Pillow 生成图像：绘制图表、生成验证码、制作表情包、合成图片。",
        "phase": "build",
    },
    {
        "name": "data-analysis",
        "description": "数据分析与可视化：Pandas 处理表格、Matplotlib 画图、统计计算、Excel 操作。",
        "phase": "build",
    },
    {
        "name": "file-organization",
        "description": "文件整理与批处理：批量重命名、分类归档、格式转换、清理临时文件。",
        "phase": "build",
    },
    {
        "name": "wechat-automation",
        "description": "微信自动化操作：给联系人发消息、发送文件、管理群聊。通过桌面 GUI 自动化实现。",
        "phase": "build",
    },
    {
        "name": "system-maintenance",
        "description": "系统维护：磁盘清理、进程管理、启动项管理、系统信息收集。",
        "phase": "build",
    },
]


class SelfLearningEngine:
    """后台自学引擎 — 启动后自动学习新技能"""

    def __init__(self):
        self.state = self._load_state()
        self.manifest = self._load_manifest()
        self._running = False
        self._task = None

    # ========== 公开接口 ==========

    async def start(self):
        """启动后台自学循环（在 main.py 启动时调用）"""
        if self._running:
            return
        self._running = True
        # 启动时：同步磁盘 + 安装常用技能 + 质量评分
        self._sync_from_disk()
        await self._install_starter_skills()
        self._archive_low_quality()
        self._save_manifest()
        self._task = asyncio.create_task(self._loop())
        print(f"[SelfLearning] 自学引擎已启动，每 {LEARN_INTERVAL//3600} 小时检查一次")

    async def stop(self):
        """停止自学循环"""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        self._save_state()

    async def learn_now(self, topic: str = "") -> dict:
        """手动触发一次学习，可选指定主题"""
        if topic:
            return await self._research_and_generate_skill(topic)
        return await self._run_learning_cycle()

    def get_manifest(self) -> dict:
        """获取完整技能清单（供 API 查询）"""
        self._sync_from_disk()
        return {
            "total": len(self.manifest["skills"]),
            "skills": self.manifest["skills"],
            "last_updated": self.manifest.get("last_updated", ""),
            "sources": [s["name"] for s in SKILL_SOURCES if s["enabled"]],
        }

    def get_skills_summary(self) -> list[dict]:
        """简化的技能摘要列表"""
        self._sync_from_disk()
        return [
            {
                "name": s["name"],
                "description": s.get("description", ""),
                "source": s.get("source", "built-in"),
                "phase": s.get("phase", ""),
                "status": s.get("status", "active"),
                "added": s.get("added", ""),
            }
            for s in self.manifest["skills"]
        ]

    def get_learning_log(self, limit: int = 50) -> list[dict]:
        """获取学习日志"""
        if not os.path.isfile(LEARNING_LOG_FILE):
            return []
        try:
            with open(LEARNING_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
            return logs[-limit:]
        except (json.JSONDecodeError, Exception):
            return []

    def _log_learning_event(self, event: dict):
        """记录一条学习事件到 learning_log.json"""
        os.makedirs(os.path.dirname(LEARNING_LOG_FILE), exist_ok=True)
        logs = []
        if os.path.isfile(LEARNING_LOG_FILE):
            try:
                with open(LEARNING_LOG_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except (json.JSONDecodeError, Exception):
                logs = []
        now = datetime.now(timezone.utc).isoformat()
        event["timestamp"] = now
        event["id"] = hashlib.md5(f"{event.get('name','')}_{now}".encode()).hexdigest()[:12]
        logs.append(event)
        with open(LEARNING_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    # ========== 核心循环 ==========

    async def _loop(self):
        """后台循环"""
        # 首次启动先同步已有技能
        self._sync_from_disk()

        while self._running:
            try:
                await self._run_learning_cycle()
            except Exception as e:
                print(f"[SelfLearning] 学习周期异常: {e}")

            # 等待下一次学习
            for _ in range(LEARN_INTERVAL // 10):
                if not self._running:
                    return
                await asyncio.sleep(10)

    async def _run_learning_cycle(self) -> dict:
        """一次完整学习周期：搜技能 → 安装 → 自学 → 记录"""
        result = {"new_skills": 0, "self_learned": 0, "details": []}

        # 1. 从 GitHub 等来源搜索新技能
        new_skills = await self._search_new_skills()
        for skill in new_skills:
            success = await self._install_skill(skill)
            if success:
                result["new_skills"] += 1
                result["details"].append(f"安装: {skill['name']}")

        # 2. 识别知识缺口并自学
        gaps = self._identify_gaps()
        for topic in gaps[:3]:  # 每次最多学 3 个
            info = await self._research_and_generate_skill(topic)
            if info:
                result["self_learned"] += 1
                result["details"].append(f"自学: {topic}")

        # 3. 质量评估 + 归档低质量技能
        self._sync_from_disk()
        self._archive_low_quality()

        # 4. 保存状态
        self._save_state()

        if result["new_skills"] or result["self_learned"]:
            print(f"[SelfLearning] 完成一轮学习: {result}")

        return result

    # ========== 搜索新技能 ==========

    async def _search_new_skills(self) -> list[dict]:
        """从各来源搜索未安装的新技能"""
        found = []
        known_names = {s["name"] for s in self.manifest["skills"]}

        for source in SKILL_SOURCES:
            if not source["enabled"]:
                continue
            try:
                if source["type"] == "github_topic":
                    skills = await self._search_github_topic(source["topic"])
                    for s in skills:
                        if s["name"] not in known_names:
                            found.append(s)
            except Exception as e:
                print(f"[SelfLearning] 搜索源 {source['name']} 失败: {e}")

        return found

    async def _search_github_topic(self, topic: str) -> list[dict]:
        """搜索 GitHub 话题，找技能仓库"""
        from tools.web_search import web_search
        from tools.web_fetch import web_fetch
        import json as _json

        # 用 GitHub API 搜索
        try:
            import httpx
            url = f"https://api.github.com/search/repositories?q=topic:{topic}+sort:updated&per_page=10"
            headers = {"Accept": "application/vnd.github.v3+json"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    skills = []
                    for repo in data.get("items", []):
                        repo_name = repo["full_name"]
                        # 检查是否已有
                        if any(s.get("repo") == repo_name for s in self.manifest["skills"]):
                            continue
                        skills.append({
                            "name": repo["name"],
                            "full_name": repo_name,
                            "description": repo.get("description", "") or "",
                            "url": repo["html_url"],
                            "source": "github",
                            "stars": repo.get("stargazers_count", 0),
                            "updated_at": repo.get("updated_at", ""),
                        })
                    return skills
        except ImportError:
            pass
        except Exception:
            pass

        # 备选：用 web_search 搜
        result = web_search(f"github topic:{topic} skill", max_results=5)
        if isinstance(result, dict) and "results" in result:
            skills = []
            for r in result["results"]:
                url = r.get("url", "")
                if "github.com" in url:
                    skills.append({
                        "name": url.split("/")[-1],
                        "url": url,
                        "description": r.get("snippet", ""),
                        "source": "github_web",
                    })
            return skills
        return []

    # ========== 安装技能 ==========

    # 尝试不同的 SKILL.md 路径（大小写、分支名）
    _SKILL_MD_PATHS = [
        "main/SKILL.md", "master/SKILL.md",
        "main/skill.md", "master/skill.md",
        "main/Skill.md", "master/Skill.md",
    ]

    async def _install_skill(self, skill_info: dict) -> bool:
        """从 GitHub 安装技能到本地"""
        name = skill_info["name"]
        target_dir = os.path.join(SKILLS_DIR, name)
        if os.path.exists(target_dir):
            if not os.path.isfile(os.path.join(target_dir, "SKILL.md")):
                try:
                    os.rmdir(target_dir)
                except OSError:
                    return False
            else:
                return False

        os.makedirs(target_dir, exist_ok=True)

        if skill_info.get("source") in ("github", "github_on_demand"):
            full_name = skill_info.get("full_name", "") or skill_info.get("repo", "")
            if not full_name:
                self._cleanup_empty_dir(target_dir)
                return False

            # 尝试多个路径下载 SKILL.md
            import httpx
            async with httpx.AsyncClient() as client:
                content = None
                used_path = ""
                for path_suffix in self._SKILL_MD_PATHS:
                    url = f"https://raw.githubusercontent.com/{full_name}/{path_suffix}"
                    try:
                        resp = await client.get(url, timeout=10)
                        if resp.status_code == 200 and len(resp.text) > 50:
                            content = resp.text
                            used_path = path_suffix
                            break
                    except Exception:
                        continue

                if content:
                    filepath = os.path.join(target_dir, "SKILL.md")
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)

                    self._add_to_manifest(name, {
                        "description": skill_info.get("description", ""),
                        "source": "github",
                        "repo": full_name,
                        "url": skill_info.get("url", ""),
                        "stars": skill_info.get("stars", 0),
                        "status": "active",
                    })

                    self._log_learning_event({
                        "type": "install",
                        "name": name,
                        "source": "github",
                        "repo": full_name,
                        "url": skill_info.get("url", ""),
                        "description": skill_info.get("description", ""),
                    })

                    self.state.setdefault("installed_repos", []).append(full_name)
                    self._save_state()

                    print(f"[SelfLearning] 安装技能: {name} ({full_name}) [{used_path}]")

                    # 安装后验证技能
                    await self._validate_skill_async(name)

                    return True

        # 安装失败，清理空目录
        self._cleanup_empty_dir(target_dir)
        return False

    async def _validate_skill_async(self, skill_name: str):
        """异步验证技能"""
        try:
            from skill_validator import validate_skill
            import asyncio

            # 在后台线程中执行验证（避免阻塞）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, validate_skill, skill_name)

            if result.get("verified"):
                print(f"[SelfLearning] 技能验证通过: {skill_name}")
            else:
                print(f"[SelfLearning] 技能验证失败: {skill_name} - {result.get('error', '')}")

            self._log_learning_event({
                "type": "validate",
                "name": skill_name,
                "verified": result.get("verified", False),
                "test_case": result.get("test_case", ""),
                "error": result.get("error", ""),
            })

        except Exception as e:
            print(f"[SelfLearning] 技能验证异常 ({skill_name}): {e}")

    def _cleanup_empty_dir(self, directory: str):
        """清理空目录"""
        try:
            if os.path.isdir(directory) and not os.listdir(directory):
                os.rmdir(directory)
                print(f"[SelfLearning] 清理空目录: {directory}")
        except OSError:
            pass

    # ========== 安装常用技能包 ==========

    async def _install_starter_skills(self):
        """启动时安装 STARTER_SKILLS 中不存在的常用技能"""
        known_names = {s["name"] for s in self.manifest["skills"]}
        installed = 0

        for skill in STARTER_SKILLS:
            name = skill["name"]
            if name in known_names:
                continue
            # 检查磁盘上是否已有
            skill_dir = os.path.join(SKILLS_DIR, name)
            if os.path.isdir(skill_dir) and os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
                self._sync_from_disk()
                known_names.add(name)
                continue

            print(f"[SelfLearning] 安装常用技能: {name}")
            # 用 LLM 生成 SKILL.md
            content = self._synthesize_skill(
                name,
                f"主题：{name}\n描述：{skill['description']}\n请生成一份完整的技能文档。"
            )
            if not content:
                continue

            # 强制修正 frontmatter 的 name 字段，防止 LLM 生成不同格式
            content = re.sub(r'^name:\s*.*$', f'name: {name}', content, count=1, flags=re.MULTILINE)

            os.makedirs(skill_dir, exist_ok=True)
            filepath = os.path.join(skill_dir, "SKILL.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            self._add_to_manifest(name, {
                "description": skill["description"],
                "source": "built-in",
                "phase": skill.get("phase", ""),
                "status": "active",
            })

            self._log_learning_event({
                "type": "starter",
                "name": name,
                "source": "built-in",
                "description": skill["description"],
            })

            installed += 1
            known_names.add(name)

        if installed:
            print(f"[SelfLearning] 已安装 {installed} 个常用技能")
        self._save_manifest()

    # ========== 自学并生成技能 ==========

    def _identify_gaps(self) -> list[str]:
        """识别知识缺口：基于失败记录动态分析 + 静态常见领域"""
        known_skills = {s["name"] for s in self.manifest["skills"]}
        already_learned = set(self.state.get("learned_topics", []))

        # 动态缺口：从失败记录中分析
        dynamic_gaps = []
        try:
            from skill_gap import recommend_skills_for_gaps
            dynamic_gaps = recommend_skills_for_gaps()
        except Exception:
            pass

        # 静态缺口：常见领域兜底
        static_gaps = [
            "web-scraping", "data-analysis", "image-processing",
            "api-development", "database-operations", "devops-automation",
            "natural-language-processing", "time-series-analysis",
        ]

        # 合并：动态优先，静态补充
        all_gaps = dynamic_gaps + [g for g in static_gaps if g not in dynamic_gaps]
        return [g for g in all_gaps if g not in known_skills and g not in already_learned]

    async def _research_and_generate_skill(self, topic: str) -> dict | None:
        """搜索一个主题，综合信息并生成 SKILL.md"""
        from tools.web_search import web_search
        from tools.web_fetch import web_fetch

        # 搜索主题相关技术
        queries = [
            f"{topic} best practices guide",
            f"{topic} tutorial how to",
            f"{topic} tools and techniques 2025",
        ]
        all_info = []
        for q in queries:
            result = web_search(q, max_results=3)
            if isinstance(result, dict) and "results" in result:
                for r in result["results"]:
                    all_info.append(f"- {r.get('title', '')}: {r.get('snippet', '')}")
                    # 抓取详细内容
                    url = r.get("url", "")
                    if url:
                        try:
                            page = await asyncio.get_event_loop().run_in_executor(
                                None, web_fetch, url
                            )
                            if isinstance(page, dict) and "content" in page:
                                all_info.append(f"  详情: {page['content'][:1500]}")
                        except Exception:
                            pass

        if not all_info:
            # 标记为已试过但没学到
            self.state.setdefault("learned_topics", []).append(topic)
            self._save_state()
            return None

        research_text = "\n".join(all_info[:20])

        # 用 LLM 综合生成 SKILL.md
        skill_content = self._synthesize_skill(topic, research_text)
        if not skill_content:
            return None

        # 写入文件
        skill_dir = os.path.join(SKILLS_DIR, topic)
        os.makedirs(skill_dir, exist_ok=True)
        filepath = os.path.join(skill_dir, "SKILL.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(skill_content)

        # 注册到 manifest
        desc = self._extract_description(skill_content)
        self._add_to_manifest(topic, {
            "description": desc,
            "source": "self-learned",
            "status": "active",
        })

        # 记录已学
        self.state.setdefault("learned_topics", []).append(topic)
        self._save_state()

        # 记录学习日志
        self._log_learning_event({
            "type": "self-learn",
            "name": topic,
            "source": "self-learned",
            "description": desc,
        })

        print(f"[SelfLearning] 自学完成: {topic}")

        # 自学完成后验证技能
        await self._validate_skill_async(topic)

        return {"topic": topic, "description": desc}

    # ========== 质量评分 + 分级 ==========

    REQUIRED_SECTIONS = ["Overview", "When to Use", "Process", "Verification"]

    def _calculate_quality_score(self, name: str, content: str, source: str = "",
                                  stars: int = 0, description: str = "") -> int:
        """
        计算技能质量分（0-100）：
        - SKILL.md 完整性（各章节）: 0-40
        - 来源加成: 0-30（built-in=30, github=20, self-learned=0）
        - GitHub stars: 0-20（min(stars/10, 20)）
        - 描述质量: 0-10
        """
        score = 0

        # 1. 章节完整性 (+0~40)
        found = 0
        content_upper = content.upper()
        for section in self.REQUIRED_SECTIONS:
            if section.upper() in content_upper:
                found += 1
        score += found * 10

        # 2. 来源加成 (+0~30)
        source_lower = source.lower()
        if source_lower == "built-in":
            score += 30
        elif source_lower == "github":
            score += 20

        # 3. GitHub stars (+0~20)
        score += min(stars, 200) // 10

        # 4. 描述质量 (+0~10)
        desc = (description or "").strip()
        if len(desc) > 50:
            score += 10
        elif len(desc) > 20:
            score += 5

        return min(score, 100)

    def _get_quality_level(self, score: int) -> str:
        """根据质量分返回等级"""
        if score >= 50:
            return "active"
        elif score >= 20:
            return "passive"
        return "archived"

    def _score_skill_on_disk(self, skill_name: str) -> tuple[int, str]:
        """对磁盘上的一个技能文件进行评分，返回 (分数, 等级)"""
        skill_path = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
        if not os.path.isfile(skill_path):
            return 0, "archived"
        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return 0, "archived"

        # 从 manifest 找来源和 stars
        source = "self-learned"
        stars = 0
        desc = ""
        for s in self.manifest["skills"]:
            if s["name"] == skill_name:
                source = s.get("source", "self-learned")
                desc = s.get("description", "")
                break

        score = self._calculate_quality_score(skill_name, content, source, stars, desc)
        level = self._get_quality_level(score)
        return score, level

    def _archive_low_quality(self):
        """扫描所有技能，更新质量分 + 将低质量的标记为 archived"""
        for s in self.manifest["skills"]:
            score, level = self._score_skill_on_disk(s["name"])
            s["quality_score"] = score
            s["quality_level"] = level

            if level == "archived" and s.get("source") != "built-in":
                was = s.get("status", "active")
                if was != "archived":
                    print(f"[SelfLearning] 归档低质量技能: {s['name']} (score={score})")
                s["status"] = "archived"
            elif level == "passive" and s.get("source") != "built-in":
                s["status"] = "passive"
            elif level == "active" and s.get("source") != "built-in":
                s["status"] = "active"
            # built-in 始终 active

        self._save_manifest()

    def _search_github_skill_for_query(self, query: str) -> list[dict]:
        """
        根据用户查询搜索 GitHub 上相关的现成技能。
        用于"提问时发现没有匹配技能，先搜 GitHub"的场景。
        """
        from tools.web_search import web_search

        search_queries = [
            f"github site:github.com {query} agent skill SKILL.md",
            f"github topic:{query} skill",
        ]
        found = []
        seen_repos = set()

        for q in search_queries:
            result = web_search(q, max_results=5)
            if not isinstance(result, dict) or "results" not in result:
                continue
            for r in result["results"]:
                url = r.get("url", "")
                if "github.com" not in url:
                    continue
                # 提取 repo full_name
                parts = url.replace("https://github.com/", "").split("/")
                if len(parts) >= 2:
                    repo = f"{parts[0]}/{parts[1]}"
                    if repo in seen_repos:
                        continue
                    seen_repos.add(repo)
                    found.append({
                        "name": parts[1],
                        "repo": repo,
                        "url": url,
                        "description": r.get("snippet", ""),
                        "source": "github_on_demand",
                    })
        return found

    def _synthesize_skill(self, topic: str, research: str) -> str | None:
        """调用 LLM 将搜索结果综合成 SKILL.md 格式"""
        try:
            from openai import OpenAI
            import httpx

            client = OpenAI(
                api_key=config.API_KEY,
                base_url=config.API_BASE_URL,
                http_client=httpx.Client(trust_env=False),
            )
            resp = client.chat.completions.create(
                model=config.MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个技能文档生成器。根据搜索到的信息，生成一个标准 SKILL.md 文件。"
                                   "格式要求：\n"
                                   "---\nname: {技能名}\ndescription: {一句话描述}\n---\n\n"
                                   "# {技能名}\n\n"
                                   "## Overview\n\n"
                                   "## When to Use\n\n"
                                   "## Process\n\n"
                                   "## Verification\n\n"
                                   "只输出 SKILL.md 内容，不要额外解释。",
                    },
                    {
                        "role": "user",
                        "content": f"主题：{topic}\n\n搜索到的参考资料：\n{research[:4000]}",
                    },
                ],
                temperature=0.3,
                timeout=60,
            )
            content = resp.choices[0].message.content
            if content and "---" in content:
                return content
            # LLM 可能没按格式，包一层
            return f"---\nname: {topic}\ndescription: 自学生成的{topic}技能\n---\n\n# {topic}\n\n{content or ''}"
        except Exception as e:
            print(f"[SelfLearning] 生成技能文档失败 ({topic}): {e}")
            return None

    @staticmethod
    def _extract_description(content: str) -> str:
        match = re.search(r"^description:\s*(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else ""

    # ========== Manifest 管理 ==========

    def _sync_from_disk(self):
        """扫描磁盘上的技能，同步到 manifest"""
        if not os.path.isdir(SKILLS_DIR):
            return

        disk_skills = set()
        for d in os.listdir(SKILLS_DIR):
            skill_path = os.path.join(SKILLS_DIR, d, "SKILL.md")
            if os.path.isfile(skill_path):
                disk_skills.add(d)
                # 如果 manifest 里没有，补上
                if not any(s["name"] == d for s in self.manifest["skills"]):
                    with open(skill_path, "r", encoding="utf-8") as f:
                        raw = f.read()
                    desc = self._extract_description(raw)
                    self._add_to_manifest(d, {
                        "description": desc,
                        "source": "built-in",
                        "status": "active",
                    })

        # 标记已删除的技能
        for s in self.manifest["skills"]:
            if s["name"] not in disk_skills and s["status"] != "learning":
                s["status"] = "removed"

        self._save_manifest()

    def _add_to_manifest(self, name: str, info: dict):
        """添加或更新技能清单条目"""
        existing = next((s for s in self.manifest["skills"] if s["name"] == name), None)
        now = datetime.now(timezone.utc).isoformat()

        # 计算质量分
        skill_path = os.path.join(SKILLS_DIR, name, "SKILL.md")
        content = ""
        if os.path.isfile(skill_path):
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                pass

        source = info.get("source", "built-in")
        stars = info.get("stars", 0)
        desc = info.get("description", "")
        quality_score = self._calculate_quality_score(name, content, source, stars, desc)
        quality_level = self._get_quality_level(quality_score)

        if existing:
            existing.update(info)
            existing["updated"] = now
            existing["quality_score"] = quality_score
            existing["quality_level"] = quality_level
        else:
            entry = {
                "name": name,
                "description": desc,
                "source": source,
                "repo": info.get("repo", ""),
                "url": info.get("url", ""),
                "phase": info.get("phase", ""),
                "status": info.get("status", "active"),
                "quality_score": quality_score,
                "quality_level": quality_level,
                "stars": stars,
                "added": info.get("added", now),
                "updated": now,
            }
            self.manifest["skills"].append(entry)

        self.manifest["last_updated"] = now
        self._save_manifest()

        if quality_level in ("passive", "archived") and source != "built-in":
            print(f"[SelfLearning] 技能 {name} 质量评级: {quality_level} (score={quality_score})")

    # ========== 状态持久化 ==========

    def _load_state(self) -> dict:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        if os.path.isfile(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                pass
        return {
            "learned_topics": [],
            "installed_repos": [],
            "last_cycle": "",
            "created": datetime.now(timezone.utc).isoformat(),
        }

    def _save_state(self):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        self.state["last_cycle"] = datetime.now(timezone.utc).isoformat()
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _load_manifest(self) -> dict:
        if os.path.isfile(MANIFEST_FILE):
            try:
                with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                pass
        return {"skills": [], "last_updated": "", "sources": []}

    def _save_manifest(self):
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)
