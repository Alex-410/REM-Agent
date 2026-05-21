# Big Agent 开发日志

## 日志规则
- 每次开发 session 记录一条
- 格式：`## YYYY-MM-DD Session N — 标题`
- 内容：做了什么、关键决策、遇到的问题、下一步计划
- 下次用 Claude Code 继续时，先读这个文件的最新一条

---

## 2026-05-20 Session 01 — 初始架构搭建 + UI 重设计

### 做了什么

**架构规划：**
- 明确了项目核心理念：**自学型电脑控制智能体**，不是预设工具的机器人
- 设计了完整五层架构：用户交互层 → 意图引擎 → 记忆与技能系统 → 计算机控制层 → LLM 模型层
- 规划了 5 个 Phase，从基建到应用场景深化
- 写入了 PLAN.md，包含完整文件结构

**模型配置层：**
- config.py 已支持 API_BASE_URL / API_KEY / MODEL_NAME 全自定义
- .env 文件管理敏感信息，可分享配置框架

**已有成果（前序工作）：**
- 17 个工具（web、代码执行、文件、图片、git、代码分析）
- 23 个 agent-skills 技能已集成
- 4 个 Persona（通用、代码审查、安全审计、测试工程师）
- 工作流状态管理（Define→Plan→Build→Verify→Review→Ship）
- 11 个 / 命令

### 关键决策
1. **自学机制**：不是预设技能库，而是 agent 自己搜方案→尝试→记住
2. **模型无关**：全部通过 OpenAI 兼容接口，换模型只需改 .env
3. **分阶段开发**：不一口气做完，每次 session 完成一个可工作的小增量
4. **日志先行**：每次写 DEVELOPMENT_LOG.md，保证衔接

### 技术选型
- 后端：Python FastAPI（已有）
- 前端：Web UI（已有，改为极简中文版）
- 桌面 UI：PyQt5（Phase 4）
- 鼠标键盘控制：pyautogui（Phase 3）
- 窗口管理：win32gui（Phase 3）
- OCR：easyocr / paddleocr（Phase 3）

### 待办事项
- [x] 写 PLAN.md
- [x] 写 DEVELOPMENT_LOG.md
- [x] Web UI 全面中文化 + Claude 极简风格
- [ ] config.py 完成全自定义配置（API endpoint / key / model）
- [ ] 启动 intent_engine.py 设计

### 下一步
下个 session 应该做的：
1. **验证当前代码** — 确保 main.py 能正常启动，API 全部可用
2. **开始 intent_engine.py** — 模糊指令拆解的第一个版本
3. **开始 memory_store.py** — 简单的 JSON 文件记忆存储

---

## 2026-05-21 Session 08 — 集成 Anthropic 官方 17 个 Skills

### 做了什么

**批量安装 Anthropic 官方 skills：**
- 从 [anthropics/skills](https://github.com/anthropics/skills) 下载全部 17 个官方 skill
- 每个 skill 的 SKILL.md 保存到 `agent-skills/skills/<name>/` 目录
- 自动解析 YAML frontmatter 获取名称和描述
- 更新 `skills_manifest.json`，标记 source=github, repo=anthropics/skills

**Skill 引擎集成：**
- `skill_engine.py` — SKILL_PHASE_MAP 新增 17 条映射（按功能分到 define/build/verify/meta/ship 阶段）
- `skill_engine.py` — SKILL_KEYWORDS 新增中英文关键词，支持模糊匹配
- 无需修改加载逻辑，`_load_skills()` 自动读取新 SKILL.md 文件

**已安装的 Anthropic Skills：**

| 分类 | Skills |
|------|--------|
| 🎨 创意 | algorithmic-art, slack-gif-creator, theme-factory |
| 📋 定义 | brand-guidelines, internal-comms |
| 🔧 构建 | canvas-design, claude-api, frontend-design, mcp-builder, skill-creator, web-artifacts-builder |
| 📝 规划 | doc-coauthoring |
| ✅ 验证 | webapp-testing |
| 🚀 交付 | docx, pdf, pptx, xlsx |

### 当前状态
- **工具：** 45 个
- **Skills：** 40 个内置 skill + 17 个 Anthropic 官方 skill = **57 个**（在 manifest 中 +30 个社区安装 = 87）
- **Persona：** 4 个
- **意图引擎：** 记忆命中 → 自学 → 方案生成 → 执行 → 记住
- **任务监控：** 后台任务追踪 API
- **桌面悬浮窗：** 截图/OCR/拖拽/任务查询

### 待办
- [x] 安装 Anthropic 官方 17 个 skill
- [x] 注册到 skill 引擎（阶段映射 + 关键词匹配）
- [ ] 桌面环境感知增强（DPI、多显示器）
- [ ] WeChat 文件发送智能化（基于 click_text）
- [ ] 任务完成通知（悬浮窗闪烁 / 桌面提醒）

### 下一步
1. **探索更多社区 skill 源** — JetBrains/skills、awesome-claude-skills 等
2. **桌面环境感知增强** — 多显示器、DPI 缩放
3. **WeChat 文件发送** — 用 click_text 定位对话框按钮
- 执行完自动保存到记忆系统

**Windows 控制工具 (tools/windows_control/)：**
- 鼠标：click, move, double_click, right_click, drag, scroll, position, screen_size
- 键盘：type, hotkey(支持中文名如"保存""复制"), press, write_enter
- 进程：list, find, launch, kill, is_running
- 窗口：list, find, activate, close, minimize, get_active

**工具注册表：17 -> 30+ 个工具**

**前端：** 新增 /do 按钮 + 意图引擎事件显示 + 自动路由 /do 到 /api/intent

**API：** 新增 /api/intent 端点

### 当前工具
web: web_search, web_fetch
code: execute_python, bash
file: read_file, write_file, list_files
image: image_search, image_fetch
git: git_status, git_diff, git_log, git_commit, git_branch, git_show
analysis: code_search, project_structure
mouse: mouse_click, mouse_move, mouse_double_click, mouse_right_click, mouse_scroll, mouse_position, get_screen_size
keyboard: keyboard_type, keyboard_hotkey, keyboard_write_enter
process: process_list, process_find, process_launch, process_kill, process_is_running
window: window_list, window_find, window_activate, window_close, window_minimize, window_get_active

### 待办
- [x] memory_store.py
- [x] intent_engine.py
- [x] tools/windows_control/
- [x] 注册新工具到 registry
- [x] agent.py 添加 /do 命令
- [x] main.py 添加 /api/intent
- [x] UI 支持意图引擎事件
- [ ] 端到端测试 /do
- [ ] 安装 pyautogui + psutil + pywin32

---

## 2026-05-20 Session 03 — 依赖安装 + 全流程端到端测试

### 做了什么

**依赖安装：**
- pip install pyautogui psutil pywin32 成功
- 修复 server 启动方式：uvicorn.run("main:app", reload=True) 替代直接传 app 对象

**全流程验证：**
- 35 个工具全部注册成功（原 17 + 18 个 Windows 控制工具）
- Windows 控制工具可用：鼠标定位、屏幕分辨率（2560×1440）正常
- /api/intent 意图引擎端到端跑通：记忆命中 → 方案生成 → 逐步骤执行 → 结果反馈
- /api/chat 正常响应
- Web UI 可访问（中文 Claude 极简风格）

### 当前状态
- 所有依赖已安装
- 系统稳定运行于 http://127.0.0.1:8000
- 35 工具 / 23 技能 / 4 Persona / 意图引擎 / 记忆系统 全部可用

### 待办
- [x] pip install pyautogui psutil pywin32
- [x] 测试 /do 写个爱心代码
- [x] 验证 Windows 控制工具
- [x] 修复 uvicorn reload 启动问题
- [ ] 意图引擎容错机制（步骤失败时自动重试 / 换方案）
- [ ] 意图引擎 - 电脑信息感知（检测已装软件、当前窗口状态）
- [ ] PyQt5 桌面悬浮窗（全局快捷键唤起）

---

## 2026-05-20 Session 04 — UI 停止按钮 + 会话持久化 + 意图引擎容错

### 做了什么

**UI 停止按钮：**
- 发送按钮旁新增 ■ 停止按钮，请求运行时显示，可随时中断 SSE 流
- 使用 AbortController 实现，中止后页面不报错，显示"⏹ 已手动停止"
- setBusy() 统一控制停止按钮的显示/隐藏

**会话持久化：**
- 每次消息变更自动保存到 localStorage（agent_messages + agent_conv_id）
- 页面刷新后自动恢复历史消息和会话 ID
- 清空按钮同时清除 localStorage
- saveMessages() 在 addMsg/sysMsg/showErr/clearAll 每个入口调用

**意图引擎容错机制：**
- execute_plan() 每步失败自动重试（最多 2 次），逐次 yield step_retry 事件
- 新增 _can_auto_fix() / _auto_fix() 自动检测"ModuleNotFoundError"等常见错误
- 自动 pip install 缺失的 Python 包，修复后自动重试该步骤
- 新增事件类型：step_retry（重试通知）、step_failed（彻底失败）、auto_fix（自动修复）
- 前端新增对应渲染：🔄 重试 / ❌ 步骤失败 / 🔧 自动修复

**其他修复：**
- uvicorn.run("main:app", reload=True) 修复热重载不生效问题

### 当前状态
- **端到端可用**：/api/chat（对话）+ /api/intent（意图执行）+ /do 命令
- **35 工具 / 23 技能 / 4 Persona** 全部注册可用
- **记忆系统**：JSON 文件持久化，自动提取关键词，模糊搜索匹配
- **Windows 控制**：鼠标 / 键盘 / 进程 / 窗口全套
- **UI**：停止按钮 + 会话持久化（刷新不丢消息）+ 意图引擎事件展示
- **容错**：步骤重试 + 自动 pip install 修复

### 待办
- [x] pip install pyautogui psutil pywin32
- [x] 测试 /do 端到端
- [x] 验证 Windows 控制工具
- [x] 修复 uvicorn reload
- [x] 停止按钮（AbortController）
- [x] 会话持久化（localStorage）
- [x] 意图引擎容错（重试 + 自动修复）
- [ ] 环境感知 — 意图引擎自动检测桌面环境（已装软件、窗口状态）
- [ ] PyQt5 桌面悬浮窗（全局快捷键 Ctrl+Space 唤起）

### 下一步
下个 session 应该做：
1. **环境感知** — 意图引擎执行前自动收集：当前活跃窗口、已安装软件列表、屏幕分辨率、网络状态，注入到规划提示中
2. **PyQt5 桌面悬浮窗** — 极简半透明输入框，Ctrl+Space 全局唤出，回车发送到 /api/intent

---

## 2026-05-20 Session 05 — 文件输出规范 + 桌面环境感知 + WeChat 端到端验证

### 做了什么

**文件输出规范 (output.py)：**
- 创建 output/ 目录结构：code/ images/ data/ temp/
- output.py 提供 get_path()、describe_structure() 等 API
- PLANNING_PROMPT 注入输出路径规则，所有生成文件必须放入对应分类目录
- agent.py 系统提示也加入文件输出规范

**桌面环境感知 (desktop_context.py)：**
- 收集：操作系统、屏幕分辨率、当前活跃窗口、已安装软件、正在运行的进程
- collect_context() 返回结构化数据，describe_desktop() 返回 LLM 友好文本
- 已安装检测：WeChat、QQ、Chrome、VS Code、Edge、Notepad、Calculator、Spotify
- 进程检测：支持关键词过滤（WeChat、QQ、chrome、code 等）

**记忆搜索修复：**
- hit_count 不再独立产生分数（之前导致"写个爱心代码"错误匹配到微信请求）
- 必须有：精确匹配 / 部分包含 / 关键词重叠 至少一种真实匹配，再加命中加成

**window_activate 修复：**
- Windows SetForegroundWindow 有焦点安全限制（非前台进程不能抢焦点）
- 增加 SwitchToThisWindow 绕过限制 + Alt 键模拟法作为双重备选
- 微信窗口激活成功验证

**端到端验证：** `/do 使用微信给Rem发送你好你在干嘛`
- Step 1: window_activate("微信") ✅ 激活微信窗口
- Step 2: keyboard_hotkey("ctrl+f") ✅ 打开搜索
- Step 3: keyboard_write_enter("Rem") ✅ 搜索联系人并进入聊天
- Step 4: keyboard_write_enter("你好你在干嘛") ✅ 输入消息并发送
- 全部 4 步成功，无失败
- 第二次调用直接命中记忆（高置信度），跳过 LLM 秒执行

### 当前状态
- 35 工具 / 23 技能 / 4 Persona / 意图引擎 / 记忆系统 / 环境感知 全部可用
- 文件输出统一到 output/ 子目录
- 桌面环境自动检测，方案生成更贴合实际
- WeChat 控制流已验证（窗口激活 → 搜索 → 输入 → 发送）
- 已知限制：微信快捷键依赖于具体窗口布局，搜索框焦点可能需调整

### 待办
- [x] 文件输出规范（output.py + PLANNING_PROMPT 注入）
- [x] 桌面环境感知（desktop_context.py）
- [x] 记忆搜索 bug 修复（hit_count 需要实际匹配才计入）
- [x] window_activate 绕过 Windows 焦点限制
- [x] WeChat 端到端验证通过
- [ ] PyQt5 桌面悬浮窗（全局快捷键 Ctrl+Space 唤起）
- [ ] 屏幕 OCR（识别 GUI 按钮/文字，精确定位点击）
- [ ] 意图引擎多步骤依赖（上一步结果传递给下一步）

### 下一步
下个 session 应该做：
1. **PyQt5 桌面悬浮窗** — 极简半透明输入框，Ctrl+Space 全局唤出，输入直接发 /api/intent
2. **屏幕 OCR 能力** — 用 easyocr/paddleocr 识别屏幕上的文字，让 agent 能"看"到按钮和输入框
3. **多步骤上下文传递** — 上一步的执行结果传递给下一步

---

## 2026-05-20 Session 07 — 桌面悬浮窗增强 + 后台任务监控系统

### 做了什么

**桌面悬浮窗增强 (desktop_overlay.py)：**
- 截图快捷键：Ctrl+Shift+S 一键全屏截图 + OCR 识别，结果直接显示在输出区
- 文件拖拽支持：拖入文件到悬浮窗 → 显示路径 → 自动填入输入框，边框高亮反馈
- 本地命令系统：`/tasks` 列出所有任务、`/task <id>` 查询状态、`/clear` 清空、`/help` 帮助
- TaskFetcher 线程：后台查询任务 API，格式化显示任务状态、进度、耗时
- 输入框提示更新，快捷键栏显示新功能

**后台任务监控系统 (task_manager.py + main.py)：**
- task_manager.py：Task/TaskManager 类，UUID 自动生成，状态追踪（pending→running→completed/failed/cancelled）
- 进度更新：current_step / total_steps / step_details，保留最近 10 步详情
- 自动清理：已完成任务最多保留 50 个，超过 24 小时自动过期
- API 端点：`/api/tasks`（列表）、`/api/task/{id}`（查询）、`/api/task/cancel/{id}`（取消）、`DELETE /api/task/{id}`（删除）
- /api/intent 集成：创建任务 → 监听 SSE 事件 → 自动更新进度 → 完成/失败标记

**其他修复：**
- git rebase 中止，工作区恢复干净
- 服务器端到端验证通过（45 工具，意图引擎、任务系统全部可用）
- 修复 Pydantic body parsing 问题

### 当前状态
- **工具：** 45 个工具注册可用
- **意图引擎：** 记忆命中 → 自学 → 方案生成 → 逐步骤执行 → 记住，完整闭环
- **桌面悬浮窗：** 截图/OCR/拖拽/任务查询/本地命令，功能全面
- **任务监控：** 后台任务全程追踪，API 可查进度和结果
- **视觉定位点击：** OCR 识别 → 定位坐标 → 自动点击，已就绪

### 待办
- [x] git rebase 清理
- [x] 视觉定位点击验证（click_text 已就绪）
- [x] 服务端到端验证
- [x] 桌面悬浮窗增强（截图快捷键、文件拖拽、本地命令）
- [x] 意图引擎后台任务监控
- [ ] 桌面环境感知增强（DPI 检测、多显示器支持）
- [ ] 更智能的 WeChat 文件发送（基于 OCR 定位文件对话框）
- [ ] 意图引擎 — 后台任务完成通知（桌面通知 / 悬浮窗提示）

### 下一步
下个 session 应该做：
1. **桌面环境感知增强** — 检测多显示器配置、DPI 缩放、更精准的已安装软件检测
2. **WeChat 文件发送智能化** — 使用 click_text 定位文件对话框的"打开"按钮
3. **任务完成通知** — 悬浮窗闪烁 / Windows 通知栏提醒

### 做了什么

**截图 + OCR 模块（tools/windows_control/screenshot.py + ocr.py）：**
- `screenshot_fullscreen` / `screenshot_region` / `screenshot_active_window` — 三种截图模式，用 mss 实现快速截图
- `ocr_screen` / `ocr_region` / `ocr_file` / `ocr_find_text` — 基于 easyocr 的屏幕文字识别，支持中英文
- `find_text_on_screen` — 搜索指定文字在屏幕上的位置，可用来定位按钮
- 截图自动保存到 output/images/ 目录
- 首次调用 easyocr 自动下载模型

**多步骤上下文传递（intent_engine.py）：**
- `_resolve_args()` — 步骤参数支持 `{step_N.result_key}` 变量替换，上一步结果可传递给下一步
- `_replan_remaining_steps()` — 步骤彻底失败后用 LLM 重新规划剩余步骤
- 前端新增 `replan` 事件类型渲染

**PyQt5 桌面悬浮窗（desktop_overlay.py）：**
- 半透明浮动输入框（92% 透明度，圆角深色），始终置顶
- Ctrl+Space 全局快捷键显示/隐藏（基于 keyboard 库）
- 回车发送到 /api/intent，流式 SSE 显示执行过程
- 所有意图引擎事件类型（step, step_result, re-plan, memory_hit 等）均支持显示
- 状态指示灯（绿色=空闲，黄色=执行中）
- 服务端地址通过 AGENT_HOST 环境变量配置（默认 http://127.0.0.1:8000）

**工具增长：35 → 44**
| 类别 | 工具数 |
|------|--------|
| web | 2 | code | 2 | file | 3 | image | 2 |
| git | 6 | analysis | 2 | mouse | 7 | keyboard | 3 |
| process | 4 | window | 6 | wechat | 2 |
| **screenshot** | **3** (fullscreen, region, active_window) |
| **ocr** | **4** (screen, region, file, find_text) |

**依赖安装：**
- mss（截图）、easyocr（OCR）、PyQt5（悬浮窗）、keyboard（全局热键）
- 修复 numpy/torchvision 版本兼容性问题（固定 numpy<2）
- 更新 requirements.txt 包含所有新依赖

### 技术细节
- easyocr 首次调用自动下载中英文模型，后续秒加载
- PyQt5 需要将 Qt DLL 目录加入 PATH（desktop_overlay.py 自动处理）
- 多步骤上下文使用 `{step_N.result_key}` 模板语法引用上一步结果
- 重新规划时，LLM 收到失败信息和已执行步骤摘要，生成替代方案

### 待办
- [x] 截图模块（screenshot.py）
- [x] OCR 模块（ocr.py）
- [x] 注册 7 个新工具到注册表
- [x] 多步骤上下文传递 + 变量替换 + 失败重新规划
- [x] PyQt5 桌面悬浮窗（Ctrl+Space 唤出）
- [x] requirements.txt 更新
- [ ] 桌面悬浮窗发送文件/图片支持
- [ ] OCR 识别后自动点击（视觉定位 + 点击）
- [ ] 更智能的 WeChat 文件发送（基于 OCR 定位文件对话框按钮）
- [ ] 意图引擎 — 长时间运行任务的后台监控

### 下一步
下个 session 应该做：
1. **视觉定位点击** — OCR 识别文字位置后自动点击（让 agent 能"看"到按钮并点击）
2. **桌面悬浮窗增强** — 支持文件拖拽发送、截图快捷键、多轮对话
3. **意图引擎后台任务** — 长时间运行的任务状态查询和进度监控
4. **桌面环境感知增强** — 检测显示器 DPI、多显示器支持、更精准的软件检测
