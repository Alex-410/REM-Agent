"""
技能集成模块 — 将学到的技能知识转化为代码修改

闭环流程：
  SKILL.md 生成 → 分析是否需要代码集成 → 生成代码 → 安全修改 → 验证 → 注册

集成模式：
  1. 新工具：技能需要新工具模块（如 pdf_gen.py）→ 创建 + 注册
  2. 增强：技能改进现有模块 → 修改现有代码
  3. 纯知识：技能只是知识文档，不需要代码修改 → 跳过
"""

import os
import json
import re
from typing import Any

from self_modifier import SelfModifier, safe_modify, safe_create

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(BASE_DIR, "agent-skills", "skills")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")

# 分析提示：判断技能是否需要代码集成
_ANALYZE_PROMPT = """分析以下技能文档，判断是否需要代码集成。

技能名称：{skill_name}
技能文档：
{skill_content}

当前已有工具：
{existing_tools}

判断规则：
1. 如果技能描述的操作可以通过现有工具完成 → 不需要代码集成
2. 如果技能需要新的 Python 库/工具来实现 → 需要新工具
3. 如果技能描述了对现有功能的改进 → 需要增强

返回 JSON：
{{
  "needs_code": true/false,
  "integration_type": "new_tool" / "enhance" / "none",
  "reason": "判断原因",
  "tool_name": "如果是 new_tool，建议的工具名",
  "tool_description": "工具描述",
  "target_file": "如果是 enhance，要修改的文件",
  "dependencies": ["需要的 Python 包列表"]
}}

只输出 JSON。"""

# 代码生成提示
_GENERATE_TOOL_PROMPT = """根据以下需求，生成一个 REM agent 工具模块。

工具名：{tool_name}
工具描述：{tool_description}
需要的依赖：{dependencies}

要求：
1. 函数签名：def {tool_name}({params}) -> dict
2. 返回 dict：成功返回数据，失败返回 {{"error": "错误信息"}}
3. 代码要完整可运行，不要占位符
4. 处理异常，不要让工具崩溃
5. 只输出 Python 代码，不要其他文字

参考已有工具的风格（简洁、返回 dict、异常处理）：
```python
def web_fetch(url: str) -> dict:
    try:
        # ... 实际逻辑
        return {{"content": "...", "title": "..."}}
    except Exception as e:
        return {{"error": str(e)}}
```"""

# 注册代码生成提示
_GENERATE_REGISTER_PROMPT = """生成工具注册代码。

工具名：{tool_name}
工具描述：{tool_description}
参数定义：{params_schema}

返回在 tools/__init__.py 的 register_all_tools 函数中需要添加的注册代码片段。
格式：
```python
from tools.{module_name} import {tool_name}
registry.register(
    "{tool_name}",
    "{tool_description}",
    {params_schema},
    {tool_name}
)
```
只输出代码片段。"""


class SkillIntegrator:
    """技能集成器 — 将学到的技能转化为代码"""

    def __init__(self):
        pass

    async def auto_integrate(self, skill_name: str) -> dict:
        """
        完整集成流程：分析 → 生成代码 → 修改 → 验证 → 注册

        返回：
          {"integrated": bool, "type": str, "message": str, "details": dict}
        """
        # 1. 读取 SKILL.md
        skill_content = self._read_skill(skill_name)
        if not skill_content:
            return {"integrated": False, "type": "none", "message": "SKILL.md 不存在"}

        # 2. 分析是否需要集成
        analysis = await self._analyze_integration(skill_name, skill_content)
        if not analysis.get("needs_code"):
            return {
                "integrated": False,
                "type": "none",
                "message": f"纯知识技能，不需要代码集成: {analysis.get('reason', '')}",
            }

        integration_type = analysis.get("integration_type", "none")

        # 3. 根据类型执行集成
        if integration_type == "new_tool":
            return await self._integrate_new_tool(skill_name, analysis)
        elif integration_type == "enhance":
            return await self._integrate_enhance(skill_name, analysis)
        else:
            return {"integrated": False, "type": "none", "message": "未知集成类型"}

    async def _analyze_integration(self, skill_name: str, skill_content: str) -> dict:
        """分析技能是否需要代码集成"""
        from llm_client import call_llm

        # 获取已有工具列表
        existing_tools = self._get_existing_tools()

        prompt = _ANALYZE_PROMPT.format(
            skill_name=skill_name,
            skill_content=skill_content[:3000],
            existing_tools=", ".join(existing_tools),
        )

        result = call_llm("你是代码集成分析器。", prompt, temperature=0.1)
        if not result:
            return {"needs_code": False, "reason": "分析器无响应"}

        return self._parse_json(result)

    async def _integrate_new_tool(self, skill_name: str, analysis: dict) -> dict:
        """集成新工具"""
        tool_name = analysis.get("tool_name", skill_name.replace("-", "_"))
        tool_desc = analysis.get("tool_description", f"{skill_name} 工具")
        dependencies = analysis.get("dependencies", [])

        # 1. 安装依赖（如果有）
        if dependencies:
            self._install_dependencies(dependencies)

        # 2. 生成工具代码
        tool_code = await self._generate_tool_code(tool_name, tool_desc, dependencies)
        if not tool_code:
            return {"integrated": False, "type": "new_tool", "message": "代码生成失败"}

        # 3. 创建工具文件（安全修改）
        tool_path = f"tools/{tool_name}.py"
        result = safe_create(tool_path, tool_code, f"auto-generated tool for skill: {skill_name}")

        if not result.get("success"):
            return {
                "integrated": False,
                "type": "new_tool",
                "message": f"创建工具文件失败: {result.get('message', '')}",
            }

        # 4. 生成注册代码并添加到 __init__.py
        register_ok = await self._register_tool(tool_name, tool_desc, tool_code)
        if not register_ok:
            return {
                "integrated": True,
                "type": "new_tool",
                "message": f"工具文件已创建，但注册失败（需手动添加到 tools/__init__.py）",
                "tool_path": tool_path,
            }

        return {
            "integrated": True,
            "type": "new_tool",
            "message": f"新工具 {tool_name} 已集成",
            "tool_path": tool_path,
        }

    async def _integrate_enhance(self, skill_name: str, analysis: dict) -> dict:
        """增强现有模块"""
        target_file = analysis.get("target_file", "")
        if not target_file:
            return {"integrated": False, "type": "enhance", "message": "未指定目标文件"}

        # 读取目标文件
        target_path = os.path.join(BASE_DIR, target_file)
        if not os.path.isfile(target_path):
            return {"integrated": False, "type": "enhance", "message": f"目标文件不存在: {target_file}"}

        with open(target_path, "r", encoding="utf-8") as f:
            current_code = f.read()

        # 用 LLM 生成增强代码
        from llm_client import call_llm
        prompt = f"""根据技能文档，增强以下代码文件。

技能：{skill_name}
技能要点：{analysis.get('reason', '')}

当前代码（{target_file}）：
{current_code[:4000]}

要求：
1. 只添加/修改必要的部分
2. 保持现有功能不变
3. 输出修改后的完整文件内容
4. 不要添加注释说明"""

        enhanced_code = call_llm("你是代码增强器。", prompt, temperature=0.1)
        if not enhanced_code:
            return {"integrated": False, "type": "enhance", "message": "代码增强生成失败"}

        # 清理 LLM 输出
        enhanced_code = self._clean_code_output(enhanced_code)

        # 安全修改
        result = safe_modify(
            target_file,
            current_code[:500],  # 用前 500 字符作为匹配锚点
            enhanced_code,
            f"auto-enhance from skill: {skill_name}",
        )

        return {
            "integrated": result.get("success", False),
            "type": "enhance",
            "message": result.get("message", ""),
            "file": target_file,
        }

    async def _generate_tool_code(self, tool_name: str, description: str, dependencies: list) -> str:
        """用 LLM 生成工具代码"""
        from llm_client import call_llm

        # 分析参数（从描述中推断）
        params = self._infer_params(tool_name, description)

        prompt = _GENERATE_TOOL_PROMPT.format(
            tool_name=tool_name,
            tool_description=description,
            dependencies=", ".join(dependencies) if dependencies else "无",
            params=", ".join(f"{p}: str" for p in params) if params else "",
        )

        result = call_llm("你是 Python 工具代码生成器。", prompt, temperature=0.2)
        if not result:
            return ""

        return self._clean_code_output(result)

    async def _register_tool(self, tool_name: str, description: str, tool_code: str) -> bool:
        """将新工具注册到 tools/__init__.py"""
        # 提取参数定义
        params = self._extract_params_from_code(tool_code, tool_name)
        params_schema = json.dumps({
            "type": "object",
            "properties": {p: {"type": "string", "description": f"{p} 参数"} for p in params},
            "required": params,
        }, ensure_ascii=False)

        # 构建注册代码
        register_code = f'''
    # --- {tool_name} (auto-registered by skill_integrator) ---
    from tools.{tool_name} import {tool_name}
    registry.register(
        "{tool_name}",
        "{description}",
        {params_schema},
        {tool_name}
    )
'''

        # 读取 __init__.py
        init_path = os.path.join(TOOLS_DIR, "__init__.py")
        with open(init_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否已注册
        if f'"{tool_name}"' in content:
            return True  # 已注册

        # 在 register_all_tools 函数末尾添加注册代码
        # 找到函数的最后一个 registry.register 调用之后
        insert_pos = content.rfind("registry.register(")
        if insert_pos == -1:
            return False

        # 找到该 register 调用的结束位置（找下一个同级语句）
        # 简单方法：在文件末尾的 return 或函数结束前插入
        # 实际上，在最后一个 register 调用的闭合括号后插入
        paren_count = 0
        end_pos = insert_pos
        for i in range(insert_pos, len(content)):
            if content[i] == "(":
                paren_count += 1
            elif content[i] == ")":
                paren_count -= 1
                if paren_count == 0:
                    end_pos = i + 1
                    break

        # 在结束位置后插入
        new_content = content[:end_pos] + "\n" + register_code + content[end_pos:]

        # 安全修改
        result = safe_modify(
            "tools/__init__.py",
            content[end_pos:end_pos + 50],  # 锚点
            content[end_pos:end_pos + 50] + "\n" + register_code,
            f"register tool: {tool_name}",
            skip_tests=True,  # __init__.py 的 import 测试可能失败（新模块还没加载）
        )

        return result.get("success", False)

    def _read_skill(self, skill_name: str) -> str:
        """读取 SKILL.md"""
        path = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
        if not os.path.isfile(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _get_existing_tools(self) -> list[str]:
        """获取已注册的工具名列表"""
        try:
            init_path = os.path.join(TOOLS_DIR, "__init__.py")
            with open(init_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 提取 registry.register("xxx", ...) 中的工具名
            return re.findall(r'registry\.register\(\s*["\']([^"\']+)["\']', content)
        except Exception:
            return []

    def _infer_params(self, tool_name: str, description: str) -> list[str]:
        """从工具名和描述推断参数"""
        params = []
        desc_lower = description.lower()

        # 常见参数模式
        if "url" in desc_lower or "网址" in desc_lower:
            params.append("url")
        if "文件" in desc_lower or "file" in desc_lower or "path" in desc_lower:
            params.append("file_path")
        if "搜索" in desc_lower or "search" in desc_lower or "query" in desc_lower:
            params.append("query")
        if "文本" in desc_lower or "text" in desc_lower or "content" in desc_lower:
            params.append("text")
        if "命令" in desc_lower or "command" in desc_lower:
            params.append("command")

        # 至少一个参数
        if not params:
            params.append("input")

        return params

    def _extract_params_from_code(self, code: str, func_name: str) -> list[str]:
        """从生成的代码中提取函数参数"""
        # 找到函数定义
        match = re.search(rf"def\s+{func_name}\s*\(([^)]*)\)", code)
        if not match:
            return ["input"]

        params_str = match.group(1)
        params = []
        for p in params_str.split(","):
            p = p.strip()
            if p and p != "self":
                # 去掉类型注解和默认值
                name = p.split(":")[0].split("=")[0].strip()
                if name:
                    params.append(name)

        return params if params else ["input"]

    def _install_dependencies(self, dependencies: list):
        """安装 Python 依赖"""
        import subprocess
        for dep in dependencies:
            try:
                subprocess.run(
                    ["pip", "install", dep],
                    capture_output=True, text=True, timeout=60,
                )
            except Exception:
                pass

    def _clean_code_output(self, code: str) -> str:
        """清理 LLM 输出的代码"""
        code = code.strip()
        # 去掉 ```python ... ``` 标记
        if code.startswith("```"):
            lines = code.split("\n")
            if len(lines) >= 3:
                # 去掉第一行和最后一行
                if lines[-1].strip() == "```":
                    code = "\n".join(lines[1:-1])
                else:
                    code = "\n".join(lines[1:])
        return code.strip()

    def _parse_json(self, text: str) -> dict:
        """解析 LLM 输出的 JSON"""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return {"needs_code": False, "reason": "JSON 解析失败"}
