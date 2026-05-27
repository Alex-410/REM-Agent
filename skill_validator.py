"""
技能验证器 — P1

自学引擎下载了 SKILL.md 就标记"已学会"，从未实际验证。
这个模块负责：
  1. 学完一个技能后，构造一个测试用例
  2. 执行测试用例
  3. 成功 → 标记 verified: true，提升质量分
  4. 失败 → 标记 verified: false，降质量分或归档

测试策略：
  - 根据 SKILL.md 的 "When to Use" 和 "Process" 生成测试场景
  - 用 LLM 生成测试代码或测试步骤
  - 执行并验证结果
"""

import json
import os
import time
from typing import Any

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(BASE_DIR, "agent-skills", "skills")
MANIFEST_FILE = os.path.join(BASE_DIR, "skills_manifest.json")


def _load_manifest() -> dict:
    """加载技能清单"""
    if not os.path.isfile(MANIFEST_FILE):
        return {"skills": [], "last_updated": ""}
    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"skills": [], "last_updated": ""}


def _save_manifest(manifest: dict):
    """保存技能清单"""
    manifest["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def _read_skill_md(skill_name: str) -> str | None:
    """读取 SKILL.md 内容"""
    path = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def _generate_test_case(skill_name: str, skill_content: str) -> dict | None:
    """
    用 LLM 根据 SKILL.md 生成测试用例。

    返回：
      {
        "description": "测试描述",
        "test_code": "要执行的 Python 代码",
        "expected": "预期结果描述"
      }
    """
    try:
        from openai import OpenAI
        import httpx

        client = OpenAI(
            api_key=config.API_KEY,
            base_url=config.API_BASE_URL,
            http_client=httpx.Client(trust_env=False),
        )

        # 提取关键章节
        sections_to_extract = ["Overview", "When to Use", "Process", "Verification"]
        extracted = []
        for section in sections_to_extract:
            # 查找章节内容
            import re
            pattern = rf"##\s*{section}\s*\n(.*?)(?=\n##|\Z)"
            match = re.search(pattern, skill_content, re.DOTALL | re.IGNORECASE)
            if match:
                extracted.append(f"## {section}\n{match.group(1).strip()}")

        skill_summary = "\n\n".join(extracted) if extracted else skill_content[:3000]

        resp = client.chat.completions.create(
            model=config.MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """你是一个技能验证器。根据技能文档生成一个简单的测试用例。

要求：
1. 测试代码必须是可直接执行的 Python 代码
2. 测试应该验证技能的核心能力
3. 测试应该简单快速，不超过 10 秒
4. 如果技能涉及外部服务（如 API、网络），用 mock 或跳过
5. 如果技能涉及 GUI 操作（如桌面自动化），用模拟数据测试

输出 JSON 格式：
{
  "description": "测试描述",
  "test_code": "Python 代码，最后 print 结果",
  "expected": "预期输出的关键词或模式"
}

只输出 JSON，不要额外解释。""",
                },
                {
                    "role": "user",
                    "content": f"技能名称：{skill_name}\n\n技能文档：\n{skill_summary[:4000]}",
                },
            ],
            temperature=0.2,
            timeout=30,
        )

        content = resp.choices[0].message.content
        if not content:
            return None

        # 提取 JSON（支持嵌套大括号）
        decoder = json.JSONDecoder()
        content_stripped = content.strip()
        # 跳过 markdown 代码块标记
        if content_stripped.startswith("```"):
            lines = content_stripped.split("\n")
            content_stripped = "\n".join(lines[1:])
            if content_stripped.rstrip().endswith("```"):
                content_stripped = content_stripped.rstrip()[:-3].rstrip()

        for i, ch in enumerate(content_stripped):
            if ch == '{':
                try:
                    obj, _ = decoder.raw_decode(content_stripped, i)
                    return obj
                except json.JSONDecodeError:
                    continue

        # 最后尝试单引号修复
        try:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                fixed = json_match.group().replace("'", '"')
                return json.loads(fixed)
        except:
            pass

        return None

    except Exception as e:
        print(f"[SkillValidator] 生成测试用例失败 ({skill_name}): {e}")
        return None


def _execute_test(test_code: str) -> dict:
    """
    执行测试代码。

    返回：
      {
        "success": True/False,
        "output": "执行输出",
        "error": "错误信息（如果有）"
      }
    """
    import subprocess
    import sys

    try:
        # 限制执行时间
        result = subprocess.run(
            [sys.executable, "-c", test_code],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=BASE_DIR,
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip()[-2000:],
            "error": result.stderr.strip()[-1000:] if result.returncode != 0 else "",
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "测试执行超时（15秒）",
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
        }


def _check_output(output: str, expected: str) -> bool:
    """检查输出是否符合预期"""
    if not expected:
        return True

    # 简单的关键词匹配
    expected_lower = expected.lower()
    output_lower = output.lower()

    # 如果预期包含多个关键词（用逗号分隔），检查是否都出现
    keywords = [k.strip() for k in expected_lower.split(",")]
    return all(k in output_lower for k in keywords if k)


def validate_skill(skill_name: str) -> dict:
    """
    验证一个技能。

    流程：
    1. 读取 SKILL.md
    2. 生成测试用例
    3. 执行测试
    4. 检查结果
    5. 更新 manifest

    返回验证结果。
    """
    # 1. 读取 SKILL.md
    skill_content = _read_skill_md(skill_name)
    if not skill_content:
        return {
            "skill": skill_name,
            "verified": False,
            "error": "SKILL.md 不存在",
        }

    # 2. 生成测试用例
    test_case = _generate_test_case(skill_name, skill_content)
    if not test_case:
        return {
            "skill": skill_name,
            "verified": False,
            "error": "无法生成测试用例",
        }

    # 3. 执行测试
    test_result = _execute_test(test_case.get("test_code", ""))

    # 4. 检查结果
    output_matches = _check_output(
        test_result.get("output", ""),
        test_case.get("expected", "")
    )

    verified = test_result.get("success", False) and output_matches

    # 5. 更新 manifest
    manifest = _load_manifest()
    for skill in manifest["skills"]:
        if skill["name"] == skill_name:
            skill["verified"] = verified
            skill["verified_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            # 调整质量分
            current_score = skill.get("quality_score", 0)
            if verified:
                # 验证通过，提升质量分
                skill["quality_score"] = min(current_score + 15, 100)
                skill["quality_level"] = _get_quality_level(skill["quality_score"])
                skill["status"] = "active"
            else:
                # 验证失败，降低质量分
                skill["quality_score"] = max(current_score - 10, 0)
                skill["quality_level"] = _get_quality_level(skill["quality_score"])
                if skill["quality_level"] == "archived":
                    skill["status"] = "archived"

            break

    _save_manifest(manifest)

    return {
        "skill": skill_name,
        "verified": verified,
        "test_case": test_case.get("description", ""),
        "test_output": test_result.get("output", "")[:500],
        "test_error": test_result.get("error", "")[:300],
        "quality_updated": True,
    }


def _get_quality_level(score: int) -> str:
    """根据质量分返回等级"""
    if score >= 50:
        return "active"
    elif score >= 20:
        return "passive"
    return "archived"


def validate_all_unverified() -> dict:
    """验证所有未验证的技能"""
    manifest = _load_manifest()
    results = []

    for skill in manifest["skills"]:
        if skill.get("verified") is None and skill.get("status") == "active":
            result = validate_skill(skill["name"])
            results.append(result)

    return {
        "total": len(results),
        "verified": sum(1 for r in results if r.get("verified")),
        "failed": sum(1 for r in results if not r.get("verified")),
        "results": results,
    }


def get_validation_summary() -> dict:
    """获取验证摘要"""
    manifest = _load_manifest()
    skills = manifest.get("skills", [])

    total = len(skills)
    verified = sum(1 for s in skills if s.get("verified"))
    unverified = sum(1 for s in skills if s.get("verified") is None)
    failed = sum(1 for s in skills if s.get("verified") is False)

    return {
        "total": total,
        "verified": verified,
        "unverified": unverified,
        "failed": failed,
        "verification_rate": round(verified / total * 100, 1) if total > 0 else 0,
    }
