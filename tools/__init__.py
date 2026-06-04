from tools.registry import ToolRegistry
from tools.web_fetch import web_fetch
from tools.web_search import web_search
from tools.execute_python import execute_python
from tools.bash import bash
from tools.file_ops import read_file, write_file, list_files
from tools.image import image_search, image_fetch
from tools.git_tools import git_status, git_diff, git_log, git_commit, git_branch, git_show
from tools.code_analysis import code_search, project_structure
from tools.windows_control import (
    mouse_click, mouse_move, mouse_double_click, mouse_right_click,
    mouse_drag, mouse_scroll, mouse_position, get_screen_size,
    keyboard_type, keyboard_hotkey, keyboard_press, keyboard_write_enter,
    process_list, process_find, process_launch, process_kill, process_is_running,
    window_list, window_find, window_activate, window_close, window_minimize,
    window_get_active,
    capture_fullscreen, capture_region, capture_active_window,
    recognize_file, recognize_screen, recognize_region,
    recognize_active_window, find_text_on_screen, click_text_on_screen,
)
from tools.wechat_send import send_text as wechat_send_text, send_file as wechat_send_file

# 共享单例 — agent.py 和 intent_engine.py 共用同一个 registry
_shared_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """返回共享的 ToolRegistry 单例，首次调用时自动注册所有工具"""
    global _shared_registry
    if _shared_registry is None:
        _shared_registry = ToolRegistry()
        register_all_tools(_shared_registry)
    return _shared_registry


def register_all_tools(registry: ToolRegistry):
    # --- Web tools ---
    registry.register(
        "web_fetch",
        "Fetch and extract the main text content from a URL. Use this to read web pages, documentation, articles.",
        {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL to fetch"}
            },
            "required": ["url"]
        },
        web_fetch
    )

    registry.register(
        "web_search",
        "Search the web for information. Returns titles, URLs and snippets. Use for any knowledge questions, news, current events.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {
                    "type": "integer", "description": "Max results (1-10)", "default": 5
                }
            },
            "required": ["query"]
        },
        web_search
    )

    # --- Code execution ---
    registry.register(
        "execute_python",
        "Execute Python code and return stdout/stderr. Use for data analysis, calculations, automation, scripting.",
        {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"}
            },
            "required": ["code"]
        },
        execute_python
    )

    registry.register(
        "bash",
        "Execute a shell command. Returns stdout/stderr and return code. Use for build tools, running scripts, system operations.",
        {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"}
            },
            "required": ["command"]
        },
        bash
    )

    # --- File operations ---
    registry.register(
        "read_file",
        "Read the contents of a file. Use to examine source code, config files, logs.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"}
            },
            "required": ["path"]
        },
        read_file
    )

    registry.register(
        "write_file",
        "Write content to a file (creates or overwrites). Use to create or modify files.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to write"}
            },
            "required": ["path", "content"]
        },
        write_file
    )

    registry.register(
        "list_files",
        "List files and directories matching a pattern. Use to explore project structure.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path", "default": "."},
                "pattern": {
                    "type": "string", "description": "Glob pattern (e.g. **/*.py)", "default": "**/*"
                }
            },
            "required": []
        },
        list_files
    )

    # --- Image tools ---
    registry.register(
        "image_search",
        "Search for images on the web. Returns image URLs and metadata.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for images"},
                "max_results": {
                    "type": "integer", "description": "Max results (1-10)", "default": 5
                }
            },
            "required": ["query"]
        },
        image_search
    )

    registry.register(
        "image_fetch",
        "Download an image from a URL and save it locally. Use after image_search to get a local copy that can be displayed.",
        {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "The direct URL of the image to download"
                }
            },
            "required": ["image_url"]
        },
        image_fetch
    )

    # --- Git tools ---
    registry.register(
        "git_status",
        "Show working tree status: modified, staged, and untracked files.",
        {
            "type": "object",
            "properties": {}
        },
        git_status
    )

    registry.register(
        "git_diff",
        "Show changes in the working tree (unstaged changes by default). Use --staged for staged changes.",
        {
            "type": "object",
            "properties": {
                "staged": {
                    "type": "boolean", "description": "Show staged changes instead of unstaged", "default": False
                },
                "path": {
                    "type": "string", "description": "Specific file path to show diff for", "default": ""
                }
            }
        },
        git_diff
    )

    registry.register(
        "git_log",
        "Show recent commit history with graph. Use to understand what changed and when.",
        {
            "type": "object",
            "properties": {
                "max_count": {
                    "type": "integer", "description": "Number of recent commits to show", "default": 10
                },
                "branch": {
                    "type": "string", "description": "Specific branch to show log for", "default": ""
                }
            }
        },
        git_log
    )

    registry.register(
        "git_commit",
        "Stage all changes and create a new git commit with the given message.",
        {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Commit message"}
            },
            "required": ["message"]
        },
        git_commit
    )

    registry.register(
        "git_branch",
        "List git branches in the repository.",
        {
            "type": "object",
            "properties": {
                "list_all": {
                    "type": "boolean", "description": "Include remote branches", "default": False
                }
            }
        },
        git_branch
    )

    registry.register(
        "git_show",
        "Show details of a specific commit (hash, author, date, message, changed files).",
        {
            "type": "object",
            "properties": {
                "commit": {
                    "type": "string", "description": "Commit reference (hash, branch, HEAD~N)", "default": "HEAD"
                }
            }
        },
        git_show
    )

    # --- Code analysis ---
    registry.register(
        "code_search",
        "Search code files for a text pattern. Use to find function definitions, variable references, imports, and any code patterns across the project.",
        {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Text pattern to search for (case-sensitive)"},
                "path": {"type": "string", "description": "Directory to search in", "default": "."},
                "max_results": {
                    "type": "integer", "description": "Maximum number of results to return", "default": 20
                }
            },
            "required": ["pattern"]
        },
        code_search
    )

    registry.register(
        "project_structure",
        "Analyze project directory structure: show file tree, file type counts, and total size. Use to understand project layout.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project root path", "default": "."},
                "max_depth": {
                    "type": "integer", "description": "How deep to traverse the tree", "default": 3
                }
            }
        },
        project_structure
    )

    # --- Windows 控制：鼠标 ---
    registry.register(
        "mouse_click",
        "在指定位置点击鼠标左键。不传坐标则在当前位置点击。用于点击按钮、链接、窗口元素。",
        {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X 坐标（可选）", "default": None},
                "y": {"type": "integer", "description": "Y 坐标（可选）", "default": None},
                "button": {"type": "string", "description": "按键：left/right/middle", "default": "left"},
                "clicks": {"type": "integer", "description": "点击次数", "default": 1},
            }
        },
        mouse_click
    )

    registry.register(
        "mouse_move",
        "移动鼠标到指定坐标。",
        {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "目标 X 坐标"},
                "y": {"type": "integer", "description": "目标 Y 坐标"},
                "duration": {"type": "number", "description": "移动持续时间（秒）", "default": 0.2},
            },
            "required": ["x", "y"]
        },
        mouse_move
    )

    registry.register(
        "mouse_double_click",
        "在指定位置双击鼠标左键。",
        {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X 坐标（可选）", "default": None},
                "y": {"type": "integer", "description": "Y 坐标（可选）", "default": None},
            }
        },
        mouse_double_click
    )

    registry.register(
        "mouse_right_click",
        "在指定位置右键单击。",
        {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X 坐标（可选）", "default": None},
                "y": {"type": "integer", "description": "Y 坐标（可选）", "default": None},
            }
        },
        mouse_right_click
    )

    registry.register(
        "mouse_scroll",
        "滚动鼠标滚轮。正数向上，负数向下。",
        {
            "type": "object",
            "properties": {
                "clicks": {"type": "integer", "description": "滚动量，正上负下"},
                "x": {"type": "integer", "description": "滚动位置 X（可选）", "default": None},
                "y": {"type": "integer", "description": "滚动位置 Y（可选）", "default": None},
            },
            "required": ["clicks"]
        },
        mouse_scroll
    )

    registry.register(
        "mouse_position",
        "获取当前鼠标位置坐标。",
        {"type": "object", "properties": {}},
        mouse_position
    )

    registry.register(
        "get_screen_size",
        "获取屏幕分辨率（宽×高）。",
        {"type": "object", "properties": {}},
        get_screen_size
    )

    # --- Windows 控制：键盘 ---
    registry.register(
        "keyboard_type",
        "模拟键盘输入文字。用于在输入框中打字。",
        {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要输入的文字"},
                "interval": {"type": "number", "description": "按键间隔（秒）", "default": 0.05},
            },
            "required": ["text"]
        },
        keyboard_type
    )

    registry.register(
        "keyboard_hotkey",
        "按下快捷键。支持格式：'ctrl+c', 'alt+tab', 'win+r' 或中文名如 '保存'、'复制'、'粘贴'。",
        {
            "type": "object",
            "properties": {
                "keys": {"type": "string", "description": "快捷键，如 ctrl+c 或中文 复制/保存/粘贴/剪切/全选/撤销/查找/运行/截图/桌面/搜索"}
            },
            "required": ["keys"]
        },
        keyboard_hotkey
    )

    registry.register(
        "keyboard_write_enter",
        "输入文字后按回车。常用于搜索框、输入框提交。",
        {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要输入的文字"}
            },
            "required": ["text"]
        },
        keyboard_write_enter
    )

    # --- Windows 控制：进程 ---
    registry.register(
        "process_launch",
        "启动一个程序。例如：notepad.exe, calc.exe, chrome.exe, code.exe。",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "程序路径或名称（如 notepad.exe, chrome.exe）"},
                "args": {"type": "string", "description": "启动参数（可选）", "default": ""},
                "wait": {"type": "boolean", "description": "是否等待程序退出", "default": False},
            },
            "required": ["path"]
        },
        process_launch
    )

    registry.register(
        "process_find",
        "按名称查找正在运行的进程。例如 'WeChat.exe', 'chrome.exe'。",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "进程名称关键词"}
            },
            "required": ["name"]
        },
        process_find
    )

    registry.register(
        "process_kill",
        "终止进程。按 PID 或名称。",
        {
            "type": "object",
            "properties": {
                "pid": {"type": "integer", "description": "进程 ID（可选）", "default": None},
                "name": {"type": "string", "description": "进程名称（可选）", "default": ""},
            }
        },
        process_kill
    )

    registry.register(
        "process_is_running",
        "检查一个程序是否正在运行。",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "进程名称"}
            },
            "required": ["name"]
        },
        process_is_running
    )

    # --- Windows 控制：窗口 ---
    registry.register(
        "window_list",
        "列出所有可见窗口。可选按标题关键词过滤。",
        {
            "type": "object",
            "properties": {
                "filter_keyword": {"type": "string", "description": "标题过滤关键词（可选）", "default": ""}
            }
        },
        window_list
    )

    registry.register(
        "window_activate",
        "激活窗口（让它获得焦点并显示到最前面）。按标题关键词查找。要操作微信窗口：window_activate('微信')",
        {
            "type": "object",
            "properties": {
                "title_keyword": {"type": "string", "description": "窗口标题关键词"}
            },
            "required": ["title_keyword"]
        },
        window_activate
    )

    registry.register(
        "window_close",
        "关闭窗口。按标题关键词查找。",
        {
            "type": "object",
            "properties": {
                "title_keyword": {"type": "string", "description": "窗口标题关键词"}
            },
            "required": ["title_keyword"]
        },
        window_close
    )

    registry.register(
        "window_get_active",
        "获取当前激活的窗口信息（标题、位置、类名）。",
        {"type": "object", "properties": {}},
        window_get_active
    )

    # --- 微信自动化 ---
    registry.register(
        "wechat_send_text",
        "给微信联系人发送文本消息。自动激活微信窗口，搜索联系人，输入消息并发送。",
        {
            "type": "object",
            "properties": {
                "contact": {"type": "string", "description": "微信联系人名称关键词，如 'rem'、'张三'"},
                "message": {"type": "string", "description": "要发送的消息文本"},
            },
            "required": ["contact", "message"]
        },
        wechat_send_text
    )

    registry.register(
        "wechat_send_file",
        "给微信联系人发送文件。自动激活微信窗口，搜索联系人，打开文件选择对话框并发送文件。",
        {
            "type": "object",
            "properties": {
                "contact": {"type": "string", "description": "微信联系人名称关键词，如 'rem'、'张三'"},
                "file_path": {"type": "string", "description": "要发送的文件的绝对路径"},
            },
            "required": ["contact", "file_path"]
        },
        wechat_send_file
    )

    # --- 截图工具 ---
    registry.register(
        "screenshot_fullscreen",
        "截取整个屏幕并保存为图片。返回图片路径。",
        {"type": "object", "properties": {}},
        capture_fullscreen
    )

    registry.register(
        "screenshot_region",
        "截取屏幕指定区域并保存为图片。",
        {
            "type": "object",
            "properties": {
                "left": {"type": "integer", "description": "区域左边界 X"},
                "top": {"type": "integer", "description": "区域上边界 Y"},
                "width": {"type": "integer", "description": "区域宽度"},
                "height": {"type": "integer", "description": "区域高度"},
            },
            "required": ["left", "top", "width", "height"]
        },
        capture_region
    )

    registry.register(
        "screenshot_active_window",
        "截取当前活跃窗口并保存为图片。返回图片路径和窗口标题。",
        {"type": "object", "properties": {}},
        capture_active_window
    )

    # --- OCR 工具 ---
    registry.register(
        "ocr_screen",
        "识别整个屏幕上的文字（中英文）。返回识别的文字列表和位置坐标。用于发现屏幕上的按钮文字、输入框提示等。",
        {"type": "object", "properties": {}},
        recognize_screen
    )

    registry.register(
        "ocr_region",
        "识别屏幕指定区域的文字。指定 left/top/width/height 区域。",
        {
            "type": "object",
            "properties": {
                "left": {"type": "integer", "description": "区域左边界"},
                "top": {"type": "integer", "description": "区域上边界"},
                "width": {"type": "integer", "description": "区域宽度"},
                "height": {"type": "integer", "description": "区域高度"},
            },
            "required": ["left", "top", "width", "height"]
        },
        recognize_region
    )

    registry.register(
        "ocr_file",
        "识别图片文件中的文字。传入图片路径。",
        {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "图片文件的路径"}
            },
            "required": ["image_path"]
        },
        recognize_file
    )

    registry.register(
        "ocr_find_text",
        "在屏幕上搜索指定的文字，返回文字位置。用于定位按钮、标签等 UI 元素。",
        {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "要搜索的文字内容"}
            },
            "required": ["target"]
        },
        find_text_on_screen
    )

    registry.register(
        "click_text",
        "在屏幕上找到指定的文字并点击它。先 OCR 识别全屏文字，找到匹配项后计算中心坐标，然后移动鼠标点击。用于点击按钮、链接、输入框等 UI 元素。",
        {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "要查找并点击的文字内容"},
                "button": {
                    "type": "string",
                    "description": "鼠标按键：left/right/double",
                    "default": "left"
                },
            },
            "required": ["target"]
        },
        click_text_on_screen
    )

    # --- 自我修改安全引擎 ---
    _self_mod_instance = None

    def _self_mod_start(description: str) -> dict:
        """启动自我修改流程：创建安全分支 self-mod/{timestamp}"""
        nonlocal _self_mod_instance
        if _self_mod_instance and _self_mod_instance.started:
            return {"error": f"已有进行中的自我修改: {_self_mod_instance.branch_name}，请先 commit 或 rollback"}
        from self_modifier import SelfModifier
        mod = SelfModifier(description)
        result = mod.start()
        if result.get("success"):
            _self_mod_instance = mod
        return result

    def _self_mod_verify(file_path: str) -> dict:
        """验证修改后的文件：语法检查 + import 测试"""
        nonlocal _self_mod_instance
        if not _self_mod_instance or not _self_mod_instance.started:
            return {"error": "没有进行中的自我修改流程，请先调用 self_mod_start"}
        return _self_mod_instance.verify(file_path)

    def _self_mod_commit(message: str) -> dict:
        """提交修改并合并回原分支，记录到 memory"""
        nonlocal _self_mod_instance
        if not _self_mod_instance or not _self_mod_instance.started:
            return {"error": "没有进行中的自我修改流程"}
        result = _self_mod_instance.commit(message)
        if result.get("success"):
            _self_mod_instance = None
        return result

    def _self_mod_rollback(reason: str = "") -> dict:
        """回滚修改，切回原分支"""
        nonlocal _self_mod_instance
        if not _self_mod_instance or not _self_mod_instance.started:
            return {"error": "没有进行中的自我修改流程"}
        result = _self_mod_instance.rollback(reason)
        _self_mod_instance = None
        return result

    def _self_mod_status() -> dict:
        """获取当前自我修改状态"""
        nonlocal _self_mod_instance
        if _self_mod_instance and _self_mod_instance.started:
            return {
                "active": True,
                "branch": _self_mod_instance.branch_name,
                "description": _self_mod_instance.description,
                "modified_files": _self_mod_instance.modified_files,
            }
        return {"active": False}

    registry.register(
        "self_mod_start",
        "【自我修改】启动安全修改流程。创建 git 分支 self-mod/{timestamp}，之后的所有文件修改都在此分支上进行。必须在 write_file 修改自己代码之前调用。",
        {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "本次修改的描述，如「优化 memory_store 搜索算法」"}
            },
            "required": ["description"]
        },
        _self_mod_start
    )

    registry.register(
        "self_mod_verify",
        "【自我修改】验证修改后的文件。检查 Python 语法和 import 是否正常。在 write_file 修改代码后、commit 之前调用。返回每项检查的通过/失败状态。",
        {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "修改后的文件路径，如 memory_store.py"}
            },
            "required": ["file_path"]
        },
        _self_mod_verify
    )

    registry.register(
        "self_mod_commit",
        "【自我修改】验证通过后提交修改。将安全分支合并回 master，删除临时分支，记录成功到 memory。失败会自动回滚。",
        {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "提交说明，如「优化搜索算法: 提升检索精度」"}
            },
            "required": ["message"]
        },
        _self_mod_commit
    )

    registry.register(
        "self_mod_rollback",
        "【自我修改】回滚所有修改。放弃安全分支上的所有改动，切回 master。验证失败时自动调用，也可手动调用。",
        {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "回滚原因（可选）", "default": ""}
            }
        },
        _self_mod_rollback
    )

    registry.register(
        "self_mod_status",
        "【自我修改】查看当前是否有进行中的自我修改流程。",
        {"type": "object", "properties": {}},
        _self_mod_status
    )

    # --- 桌面操作序列回放 ---
    def _replay_start(name: str) -> dict:
        """开始录制桌面操作序列"""
        from desktop_replay import start_recording
        return start_recording(name)

    def _replay_stop(save: bool = True) -> dict:
        """停止录制并保存"""
        from desktop_replay import stop_recording
        return stop_recording(save=save)

    def _replay_list() -> dict:
        """列出所有录制的操作序列"""
        from desktop_replay import list_sequences
        return list_sequences()

    def _replay_run(name: str, speed: float = 1.0, dry_run: bool = False) -> dict:
        """回放一个录制的操作序列。speed=回放速度倍数，dry_run=只预览不执行"""
        from desktop_replay import replay_sync
        return replay_sync(name, speed=speed, dry_run=dry_run)

    def _replay_delete(name: str) -> dict:
        """删除一个录制的操作序列"""
        from desktop_replay import delete_sequence
        return delete_sequence(name)

    def _replay_status() -> dict:
        """查看当前录制状态"""
        from desktop_replay import get_recording_status
        return get_recording_status()

    registry.register(
        "replay_start",
        "【操作回放】开始录制桌面操作。之后的鼠标、键盘、窗口操作会被记录到序列中。",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "序列名称，如 '打开记事本输入文字'"}
            },
            "required": ["name"]
        },
        _replay_start
    )

    registry.register(
        "replay_stop",
        "【操作回放】停止录制并保存序列。",
        {
            "type": "object",
            "properties": {
                "save": {"type": "boolean", "description": "是否保存录制", "default": True}
            }
        },
        _replay_stop
    )

    registry.register(
        "replay_list",
        "【操作回放】列出所有已录制的操作序列。",
        {"type": "object", "properties": {}},
        _replay_list
    )

    registry.register(
        "replay_run",
        "【操作回放】回放一个录制的操作序列。支持调节速度和预览模式。",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "序列名称"},
                "speed": {"type": "number", "description": "回放速度倍数（1.0=原速，2.0=2倍速）", "default": 1.0},
                "dry_run": {"type": "boolean", "description": "预览模式：只显示步骤不执行", "default": False},
            },
            "required": ["name"]
        },
        _replay_run
    )

    registry.register(
        "replay_delete",
        "【操作回放】删除一个已录制的操作序列。",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "序列名称"}
            },
            "required": ["name"]
        },
        _replay_delete
    )

    registry.register(
        "replay_status",
        "【操作回放】查看当前录制状态。",
        {"type": "object", "properties": {}},
        _replay_status
    )

    # --- P0: 自修改安全引擎 ---
    def _safety_check(command: str = "", filepath: str = "", operation: str = "") -> dict:
        """综合安全检查：检测危险命令、受保护文件操作"""
        from self_modify_safety import full_safety_check
        return full_safety_check(command=command, filepath=filepath, operation=operation)

    def _safety_snapshot(files: list[str] | None = None) -> dict:
        """创建核心文件快照，用于回滚"""
        from self_modify_safety import create_snapshot
        snap_id = create_snapshot(files)
        return {"snapshot_id": snap_id, "message": f"快照已创建: {snap_id}"}

    def _safety_restore(snapshot_id: str) -> dict:
        """从快照恢复核心文件"""
        from self_modify_safety import restore_snapshot
        return restore_snapshot(snapshot_id)

    def _safety_snapshots() -> dict:
        """列出所有安全快照"""
        from self_modify_safety import list_snapshots
        return {"snapshots": list_snapshots()}

    def _safety_audit(limit: int = 50) -> dict:
        """查看安全审计日志"""
        from self_modify_safety import get_audit_log
        return {"logs": get_audit_log(limit)}

    registry.register(
        "safety_check",
        "【安全引擎】综合安全检查：检测危险 shell 命令、受保护文件操作、危险代码模式。在执行高风险操作前调用。",
        {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要检查的 shell 命令（可选）", "default": ""},
                "filepath": {"type": "string", "description": "要操作的文件路径（可选）", "default": ""},
                "operation": {"type": "string", "description": "操作类型：delete/overwrite（可选）", "default": ""},
            }
        },
        _safety_check
    )

    registry.register(
        "safety_snapshot",
        "【安全引擎】创建核心文件快照。修改自己代码前调用，以便出错时回滚。",
        {
            "type": "object",
            "properties": {
                "files": {"type": "array", "items": {"type": "string"}, "description": "要快照的文件列表（可选，默认核心文件）"}
            }
        },
        _safety_snapshot
    )

    registry.register(
        "safety_restore",
        "【安全引擎】从快照恢复核心文件。修改出错时一键回退。",
        {
            "type": "object",
            "properties": {
                "snapshot_id": {"type": "string", "description": "快照 ID"}
            },
            "required": ["snapshot_id"]
        },
        _safety_restore
    )

    registry.register(
        "safety_snapshots",
        "【安全引擎】列出所有安全快照。",
        {"type": "object", "properties": {}},
        _safety_snapshots
    )

    registry.register(
        "safety_audit",
        "【安全引擎】查看安全审计日志：拦截记录、检查历史。",
        {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "返回条数", "default": 50}
            }
        },
        _safety_audit
    )

    # --- 工具链式调用 ---

    def _batch_tools(calls: list) -> dict:
        """
        批量执行多个工具调用。

        参数 calls: 工具调用列表，每个元素为 {"tool": "工具名", "args": {...}}
        返回: {"results": [{"tool": ..., "result": ...}, ...], "success_count": N, "fail_count": N}
        """
        import asyncio

        if not calls or not isinstance(calls, list):
            return {"error": "calls 参数必须是非空列表"}

        results = []
        success_count = 0
        fail_count = 0

        loop = asyncio.new_event_loop()
        try:
            for call in calls:
                tool_name = call.get("tool", "")
                tool_args = call.get("args", {})

                if not tool_name:
                    results.append({"tool": tool_name, "result": {"error": "缺少 tool 参数"}})
                    fail_count += 1
                    continue

                try:
                    result = loop.run_until_complete(registry.execute(tool_name, tool_args))
                    is_error = isinstance(result, dict) and result.get("error")
                    results.append({"tool": tool_name, "result": result})
                    if is_error:
                        fail_count += 1
                    else:
                        success_count += 1
                except Exception as e:
                    results.append({"tool": tool_name, "result": {"error": str(e)}})
                    fail_count += 1
        finally:
            loop.close()

        return {
            "results": results,
            "total": len(calls),
            "success_count": success_count,
            "fail_count": fail_count,
        }

    registry.register(
        "batch_tools",
        "批量执行多个工具调用。用于一次性完成多个操作，减少往返。每个调用格式：{\"tool\": \"工具名\", \"args\": {...}}",
        {
            "type": "object",
            "properties": {
                "calls": {
                    "type": "array",
                    "description": "工具调用列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {"type": "string", "description": "工具名"},
                            "args": {"type": "object", "description": "工具参数"}
                        },
                        "required": ["tool", "args"]
                    }
                }
            },
            "required": ["calls"]
        },
        _batch_tools
    )
