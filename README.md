# REM Agent

**Reforge, Evolvere, Mimir** — 一个具有自我进化能力的 AI Agent 系统

## 功能特性

- **智能对话**：基于大语言模型的自然语言交互
- **工具调用**：支持代码执行、文件操作、网页搜索等工具
- **自我学习**：自动学习新技能并优化自身能力
- **技能系统**：可扩展的技能框架，支持动态加载
- **记忆系统**：长期记忆和上下文管理
- **桌面交互**：支持屏幕截图、GUI 自动化等桌面操作

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制并编辑 `.env` 文件：

```bash
cp .env.example .env
```

在 `.env` 中配置以下变量：

```env
# 必填：API 配置
API_KEY=your_api_key_here
API_BASE_URL=https://api.deepseek.com
MODEL=deepseek-v4-flash

# 可选：Agent 参数
MAX_ITERATIONS=30
TOOL_TIMEOUT=60
MAX_TOOL_RESULT_LENGTH=5000

# 可选：代理设置
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

# 可选：Ollama 本地模型（用于长期记忆）
OLLAMA_HOST=http://127.0.0.1:11434
EMBED_MODEL=qwen3-embedding:0.6b
```

### 3. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

## 项目结构

```
├── main.py                 # FastAPI 主服务
├── agent.py                # Agent 核心逻辑
├── config.py               # 配置管理
├── llm_client.py           # LLM API 客户端
├── intent_engine.py        # 意图识别引擎
├── skill_engine.py         # 技能执行引擎
├── skill_integrator.py     # 技能集成器
├── self_learning.py        # 自我学习引擎
├── self_modifier.py        # 自我修改器
├── memory_store.py         # 记忆存储系统
├── observation_engine.py   # 观察引擎
├── adaptation_engine.py    # 适应引擎
├── persona_manager.py      # 人格管理器
├── task_manager.py         # 任务管理器
├── workflow_state.py       # 工作流状态管理
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量示例
└── agent-skills/           # 技能库
```

## 使用示例

### 基本对话

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，请介绍一下自己"}'
```

### 执行任务

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我写一个 Hello World 程序"}'
```

## 配置说明

### 模型配置

支持任何兼容 OpenAI 格式的 API：

- DeepSeek
- OpenAI
- Azure OpenAI
- 本地模型（如 Ollama）

### 代理配置

如果需要使用代理访问网络，在 `.env` 中设置：

```env
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

## 开发指南

### 添加新技能

1. 在 `agent-skills/skills/` 目录下创建新的技能文件
2. 实现技能接口
3. 重启服务自动加载

### 扩展工具集

在 `tools/` 目录下添加新的工具模块，系统会自动识别和调用。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
