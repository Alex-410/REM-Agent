"""
输出路径管理 — 所有生成的文件（代码、图片、数据）统一存放
"""

import os

# 输出根目录（相对项目根）
OUTPUT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# 子目录
SUBDIRS = {
    "code":   os.path.join(OUTPUT_ROOT, "code"),    # 生成的代码文件
    "images": os.path.join(OUTPUT_ROOT, "images"),  # 下载/生成的图片
    "data":   os.path.join(OUTPUT_ROOT, "data"),    # 数据文件、导出
    "temp":   os.path.join(OUTPUT_ROOT, "temp"),    # 临时文件
}


def ensure_dirs():
    """确保所有输出目录存在"""
    for d in SUBDIRS.values():
        os.makedirs(d, exist_ok=True)


def get_path(category: str, filename: str) -> str:
    """
    获取分类目录下的完整文件路径。

    category: code / images / data / temp
    filename: 文件名（如 heart.py, screenshot.png）
    """
    ensure_dirs()
    base = SUBDIRS.get(category, SUBDIRS["temp"])
    return os.path.join(base, filename)


def get_output_root() -> str:
    """获取输出根目录的绝对路径"""
    ensure_dirs()
    return OUTPUT_ROOT


def describe_structure() -> str:
    """返回目录结构描述，供 LLM 提示使用"""
    ensure_dirs()
    lines = ["输出文件必须放在以下目录："]
    for name, path in SUBDIRS.items():
        lines.append(f"  {name}/  ->  {path}/")
    lines.append("")
    lines.append("规则：")
    lines.append("  - 所有新创建的代码文件放到 code/ 目录")
    lines.append("  - 下载或生成的图片放到 images/ 目录")
    lines.append("  - 导出的数据文件放到 data/ 目录")
    lines.append("  - 临时文件放到 temp/ 目录")
    lines.append("  - 写入文件时 path 参数用绝对路径")
    return "\n".join(lines)
