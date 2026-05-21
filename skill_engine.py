import os
import re
from pathlib import Path

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent-skills", "skills")

PHASE_ORDER = ["define", "plan", "build", "verify", "review", "ship"]
PHASE_LABELS = {
    "meta": "Meta",
    "define": "Define",
    "plan": "Plan",
    "build": "Build",
    "verify": "Verify",
    "review": "Review",
    "ship": "Ship",
}
PHASE_EMOJIS = {
    "meta": "🎯",
    "define": "📋",
    "plan": "🗺️",
    "build": "🔧",
    "verify": "✅",
    "review": "👁️",
    "ship": "🚀",
}

# Map skill directories to phases
SKILL_PHASE_MAP = {
    "interview-me": "define",
    "idea-refine": "define",
    "spec-driven-development": "define",
    "planning-and-task-breakdown": "plan",
    "incremental-implementation": "build",
    "context-engineering": "build",
    "source-driven-development": "build",
    "doubt-driven-development": "build",
    "frontend-ui-engineering": "build",
    "api-and-interface-design": "build",
    "test-driven-development": "build",
    "browser-testing-with-devtools": "verify",
    "debugging-and-error-recovery": "verify",
    "code-review-and-quality": "review",
    "code-simplification": "review",
    "security-and-hardening": "review",
    "performance-optimization": "review",
    "git-workflow-and-versioning": "ship",
    "ci-cd-and-automation": "ship",
    "deprecation-and-migration": "ship",
    "documentation-and-adrs": "ship",
    "shipping-and-launch": "ship",
    "using-agent-skills": "meta",
    # Anthropic 官方 skills
    "algorithmic-art": "meta",
    "brand-guidelines": "define",
    "canvas-design": "build",
    "claude-api": "build",
    "doc-coauthoring": "plan",
    "docx": "ship",
    "frontend-design": "build",
    "internal-comms": "define",
    "mcp-builder": "build",
    "pdf": "ship",
    "pptx": "ship",
    "skill-creator": "build",
    "slack-gif-creator": "meta",
    "theme-factory": "define",
    "web-artifacts-builder": "build",
    "webapp-testing": "verify",
    "xlsx": "ship",
}

# Keyword-to-skill matching rules
SKILL_KEYWORDS = {
    "interview-me": ["interview", "grill", "clarify", "underspecified", "需求不清晰", "追问", "确认需求"],
    "idea-refine": ["idea", "brainstorm", "concept", "explore", "rough", "vague", "想法", "脑暴", "构思", "点子"],
    "spec-driven-development": ["spec", "specification", "prd", "requirement", "define", "需求文档", "规格", "功能定义"],
    "planning-and-task-breakdown": ["plan", "task", "break down", "decompose", "estimate", "scope", "规划", "拆解任务", "分工", "排期"],
    "incremental-implementation": ["implement", "build", "code", "develop", "slice", "increment", "实现", "开发", "编码", "写代码"],
    "context-engineering": ["context", "load", "background", "understand codebase", "理解项目", "上下文", "项目背景"],
    "source-driven-development": ["source", "documentation", "verify", "official", "docs", "查文档", "官方文档", "求证"],
    "doubt-driven-development": ["doubt", "review decision", "adversarial", "high stakes", "质疑", "推翻", "高风险", "关键决策"],
    "frontend-ui-engineering": ["ui", "frontend", "component", "react", "vue", "css", "design system", "前端", "界面", "组件", "样式", "页面布局"],
    "api-and-interface-design": ["api", "interface", "endpoint", "contract", "rest", "graphql", "接口", "api设计", "接口定义"],
    "test-driven-development": ["test", "tdd", "coverage", "red-green", "unittest", "测试", "单元测试", "覆盖率", "测试驱动"],
    "browser-testing-with-devtools": ["browser", "devtools", "console", "network", "dom", "e2e", "浏览器", "调试", "控制台"],
    "debugging-and-error-recovery": ["debug", "bug", "error", "fix", "broken", "crash", "fail", "调试", "报错", "崩溃", "修bug", "异常"],
    "code-review-and-quality": ["review", "cr", "code quality", "代码审查", "代码质量", "review代码"],
    "code-simplification": ["simplify", "refactor", "clean", "complex", "overengineer", "简化", "重构", "清理代码", "过度设计"],
    "security-and-hardening": ["security", "vulnerability", "owasp", "xss", "injection", "auth", "安全", "漏洞", "防护", "权限"],
    "performance-optimization": ["performance", "slow", "optimize", "lcp", "bundle", "latency", "性能", "优化", "慢", "卡顿", "加载速度"],
    "git-workflow-and-versioning": ["git", "commit", "branch", "version", "merge", "版本管理", "分支", "提交", "合并"],
    "ci-cd-and-automation": ["ci", "cd", "pipeline", "deploy", "automation", "github action", "部署", "自动化流水线", "发布流程"],
    "deprecation-and-migration": ["deprecat", "migrat", "sunset", "legacy", "remove", "迁移", "废弃", "升级", "兼容"],
    "documentation-and-adrs": ["doc", "adr", "readme", "document", "changelog", "文档", "说明文档", "变更记录"],
    "shipping-and-launch": ["ship", "launch", "deploy", "release", "rollout", "production", "上线", "发布", "生产环境", "灰度"],
    # STARTER_SKILLS 中文关键词
    "windows-automation": ["windows", "桌面", "窗口", "鼠标", "键盘", "截图", "自动化操作", "gui自动化", "桌面应用"],
    "web-scraping": ["爬虫", "抓取", "爬数据", "采集", "网页数据", "信息提取", "scrape"],
    "image-generation": ["图片", "图像", "生成图片", "画图", "验证码", "表情包", "合成图片", "pillow"],
    "data-analysis": ["数据分析", "分析数据", "数据可视化", "统计", "图表", "pandas", "excel处理", "数据表", "报表"],
    "file-organization": ["文件整理", "批量重命名", "归档", "格式转换", "清理文件", "文件管理"],
    "wechat-automation": ["微信", "发消息", "微信群", "微信好友", "微信自动化", "发送文件"],
    "system-maintenance": ["系统维护", "磁盘清理", "进程管理", "系统信息", "启动项", "电脑清理"],
    # Anthropic 官方 skills
    "algorithmic-art": ["算法艺术", "生成艺术", "创意编程", "生成式艺术", "algorithmic", "generative art", "creative coding"],
    "brand-guidelines": ["品牌规范", "品牌指南", "VI", "视觉识别", "品牌设计", "brand", "视觉规范"],
    "canvas-design": ["画布设计", "原型设计", "网页设计稿", "设计工具", "canvas", "prototype"],
    "claude-api": ["claude api", "anthropic", "sdk", "prompt caching", "claude模型", "claude sdk", "api调用"],
    "doc-coauthoring": ["文档协作", "协同编辑", "共同写作", "文档共创", "coauthor", "collaborative writing"],
    "docx": ["word文档", "docx", "word文件", "文档生成", "报告生成", "word document"],
    "frontend-design": ["前端设计", "UI设计", "界面设计", "网页设计", "landing page", "frontend", "ui design"],
    "internal-comms": ["内部沟通", "公司通知", "团队公告", "内部通讯", "internal communication", "team announcement"],
    "mcp-builder": ["mcp", "mcp server", "model context protocol", "工具开发", "mcp服务", "mcp工具"],
    "pdf": ["pdf", "pdf文档", "pdf处理", "pdf生成", "pdf编辑", "pdf文件", "文档格式"],
    "pptx": ["ppt", "pptx", "幻灯片", "演示文稿", "powerpoint", "幻灯片制作"],
    "skill-creator": ["创建skill", "技能开发", "skill开发", "编写skill", "agent skill", "skill模板"],
    "slack-gif-creator": ["slack", "gif", "动图", "表情动图", "slack表情", "gif动画"],
    "theme-factory": ["主题", "皮肤", "主题制作", "界面主题", "颜色主题", "theme", "color scheme"],
    "web-artifacts-builder": ["web artifact", "网页构件", "交互式网页", "可视化组件", "web组件", "artifacts"],
    "webapp-testing": ["web测试", "浏览器测试", "e2e测试", "前端测试", "页面测试", "web testing", "e2e"],
    "xlsx": ["excel", "xlsx", "电子表格", "表格处理", "excel文件", "数据表格", "报表生成"],
}


class SkillDefinition:
    def __init__(self, name: str, description: str, phase: str, content: str,
                 filepath: str, summary: str = ""):
        self.name = name
        self.description = description
        self.phase = phase
        self.content = content
        self.filepath = filepath
        self.summary = summary

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "phase": self.phase,
            "phase_label": PHASE_LABELS.get(self.phase, self.phase),
            "phase_emoji": PHASE_EMOJIS.get(self.phase, ""),
            "summary": self.summary,
        }


class SkillEngine:
    def __init__(self):
        self.skills: dict[str, SkillDefinition] = {}
        self._status_map: dict[str, str] = {}  # skill_name → active/passive/archived
        self._load_skills()
        self._load_status_map()

    def _load_status_map(self):
        """从 skills_manifest.json 加载技能状态映射"""
        manifest_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "skills_manifest.json"
        )
        if not os.path.isfile(manifest_path):
            return
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            for s in manifest.get("skills", []):
                self._status_map[s["name"]] = s.get("status", "active")
        except Exception:
            pass

    def _load_skills(self):
        if not os.path.isdir(SKILLS_DIR):
            return

        for skill_dir in sorted(os.listdir(SKILLS_DIR)):
            skill_path = os.path.join(SKILLS_DIR, skill_dir, "SKILL.md")
            if not os.path.isfile(skill_path):
                continue

            with open(skill_path, "r", encoding="utf-8") as f:
                raw = f.read()

            name = skill_dir
            description = ""
            content = raw

            # Parse YAML frontmatter
            frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
            if frontmatter_match:
                fm_text = frontmatter_match.group(1)
                for line in fm_text.split("\n"):
                    m = re.match(r"^name:\s*(.+)$", line)
                    if m:
                        name = m.group(1).strip()
                        continue
                    m = re.match(r"^description:\s*(.+)$", line)
                    if m:
                        description = m.group(1).strip()
                content = raw[frontmatter_match.end():]

            phase = SKILL_PHASE_MAP.get(skill_dir, "meta")
            summary = self._extract_summary(content)

            self.skills[name] = SkillDefinition(
                name=name,
                description=description,
                phase=phase,
                content=content,
                filepath=skill_path,
                summary=summary,
            )

    @staticmethod
    def _extract_summary(content: str) -> str:
        """Extract a brief summary from the skill content."""
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("#") and not line.startswith("##"):
                return line.lstrip("#").strip()
        return ""

    def get_skill(self, name: str) -> SkillDefinition | None:
        return self.skills.get(name)

    def get_all_skills(self, include_archived: bool = False) -> list[SkillDefinition]:
        if include_archived:
            return list(self.skills.values())
        return [s for s in self.skills.values()
                if self._status_map.get(s.name, "active") != "archived"]

    def get_skills_by_phase(self, phase: str) -> list[SkillDefinition]:
        return [s for s in self.skills.values() if s.phase == phase]

    def find_matching_skills(self, text: str) -> list[SkillDefinition]:
        """Match user input text to relevant skills using keyword matching.
        只返回 active + passive 的技能，active 优先。"""
        text_lower = text.lower()
        scores = {}

        for skill_name, keywords in SKILL_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw in text_lower:
                    score += 1
            if score > 0:
                scores[skill_name] = score

        # Also check description match
        for skill in self.skills.values():
            if skill.name not in scores:
                desc_lower = skill.description.lower()
                words = set(text_lower.split())
                match_count = sum(1 for w in words if len(w) > 3 and w in desc_lower)
                if match_count >= 2:
                    scores[skill.name] = scores.get(skill.name, 0) + match_count

        # 按分数排序
        ranked = sorted(scores.items(), key=lambda x: -x[1])

        # 按状态分组：active 优先，passive 次之，排除 archived
        active = []
        passive = []
        for name, score in ranked:
            skill = self.skills.get(name)
            if not skill:
                continue
            status = self._status_map.get(name, "active")
            if status == "archived":
                continue
            if status == "passive":
                passive.append(skill)
            else:
                active.append(skill)

        # 最多返回 5 个，active 在前
        result = active[:3] + passive[:2]
        return result[:5]

    def get_skill_content_section(self, skill_name: str, section: str = "overview") -> str:
        """Get a specific section of a skill's content."""
        skill = self.skills.get(skill_name)
        if not skill:
            return ""

        content = skill.content
        # Try to find ## Section header
        pattern = rf"##\s*{re.escape(section)}.*?(?=##\s|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(0).strip()
        return ""

    def get_phase_workflow_prompt(self, phase: str) -> str:
        """Get a concise workflow prompt for a phase."""
        skills = self.get_skills_by_phase(phase)
        if not skills:
            return ""

        lines = [f"## {PHASE_LABELS.get(phase, phase)} Phase", ""]
        for s in skills:
            lines.append(f"- **{s.name}**: {s.description}")
        return "\n".join(lines)

    def get_lifecycle_overview(self) -> str:
        """Get a complete lifecycle overview prompt."""
        parts = ["## Development Lifecycle", "",
                 "I follow this lifecycle for software work:"]
        for phase in PHASE_ORDER:
            skills = self.get_skills_by_phase(phase)
            emoji = PHASE_EMOJIS.get(phase, "")
            label = PHASE_LABELS.get(phase, phase)
            skill_list = ", ".join(s.name for s in skills)
            parts.append(f"{emoji} **{label}**: {skill_list}")
        parts.extend([
            "",
            "When a user request comes in, I determine which phase and skill applies, "
            "then follow that skill's workflow.",
            "Users can also use commands like /spec, /plan, /build, /test, /review, /ship "
            "to jump directly to a phase.",
        ])
        return "\n".join(parts)

    def get_active_skill_prompt(self, skill_name: str) -> str:
        """Get the full workflow instructions for an active skill."""
        skill = self.skills.get(skill_name)
        if not skill:
            return ""

        content = skill.content

        # Extract key sections: Overview, Process/Workflow, When to Use, Rules
        sections = []
        for header in ["Overview", "When to Use", "Process", "Workflow",
                       "Core Process", "The Gated Workflow", "The Increment Cycle",
                       "Rules", "Implementation Rules"]:
            pattern = rf"##\s*{re.escape(header)}.*?(?=##\s|\Z)"
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                sections.append(match.group(0).strip())

        if sections:
            return f"## Active Skill: {skill.name}\n\n" + "\n\n".join(sections)
        # Fallback: return first 1500 chars
        return f"## Active Skill: {skill.name}\n\n{content[:1500]}"
