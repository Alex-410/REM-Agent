"""
REM 配置模块 — Reforge, Evolvere, Mimir

======= 给别人用 =======
别人拿到这个项目，只需要：
1. 复制 .env 文件
2. 修改 API_KEY、API_BASE_URL、MODEL 三个变量
3. 运行 python main.py
即可使用，无需改任何代码。
========================
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 项目根目录 — 所有路径基于此计算
# ============================================================
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
# 模型配置 — 兼容任何 OpenAI 格式的 API
# 修改 .env 文件即可切换，无需改代码
# ============================================================

# 优先使用通用变量名，向后兼容 DEEPSEEK_ 前缀
API_KEY = os.getenv("API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("MODEL") or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# 别名，agent.py 里统一用 config.API_KEY / config.API_BASE_URL / config.MODEL
DEEPSEEK_API_KEY = API_KEY
DEEPSEEK_BASE_URL = API_BASE_URL
DEEPSEEK_MODEL = MODEL

# ============================================================
# 备用模型（fallback 链）
# 格式：MODEL_FALLBACKS=模型1,模型2,模型3（逗号分隔）
# 主模型失败时按顺序尝试备用模型
# ============================================================

MODEL_FALLBACKS = [
    m.strip() for m in os.getenv("MODEL_FALLBACKS", "").split(",") if m.strip()
]

# ============================================================
# Agent 运行参数
# ============================================================

# 单次任务最大迭代次数（防止无限循环）
# QQ/微信自动化等复杂任务需要更多轮次，可在 .env 中设置 MAX_ITERATIONS=40
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "30"))

# 单次工具调用超时（秒）
TOOL_TIMEOUT = int(os.getenv("TOOL_TIMEOUT", "60"))

# 工具结果最大长度
MAX_TOOL_RESULT_LENGTH = int(os.getenv("MAX_TOOL_RESULT_LENGTH", "5000"))

# ============================================================
# 网络代理（可选）
# 如果需要在代理环境下使用 web 工具，设置 HTTP_PROXY
# ============================================================

HTTP_PROXY = os.getenv("HTTP_PROXY", "")
HTTPS_PROXY = os.getenv("HTTPS_PROXY", "") or HTTP_PROXY

# 关键：从系统环境变量中移除代理！
# load_dotenv() 把 .env 的 HTTP_PROXY 写进了 os.environ，
# 导致所有子进程（bash、pip install、curl 等）都继承代理，
# 代理软件一关就连不上。
#
# web 工具（web_search、web_fetch）会通过 config.get_proxies()
# 显式获取代理配置，不受影响。
# API 调用（DeepSeek、Ollama）已用 trust_env=False / ProxyHandler({}) 绕过。
if HTTP_PROXY:
    for _key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        os.environ.pop(_key, None)


# ============================================================
# Ollama 本地模型配置（用于长期记忆的 embedding）
# ============================================================

# Ollama 服务地址
ollama_raw = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
if not ollama_raw.startswith("http"):
    ollama_raw = f"http://{ollama_raw}"
# 去除可能的前导 0.0.0.0，改成 127.0.0.1
OLLAMA_HOST = ollama_raw.replace("0.0.0.0", "127.0.0.1")

# Embedding 模型名
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:0.6b")


def get_proxies() -> dict:
    """获取 requests 库用的代理配置"""
    if HTTP_PROXY:
        return {
            "http": HTTP_PROXY,
            "https": HTTPS_PROXY or HTTP_PROXY,
        }
    return {}
