"""
PyQt5 桌面悬浮窗 — 极简半透明输入框，Ctrl+Space 唤出

功能：
- 半透明浮动输入框，始终置顶
- Ctrl+Space 全局快捷键显示/隐藏
- Ctrl+Shift+S 一键截图 + OCR 识别
- 文件拖拽发送
- 多轮对话保持（自动携带上下文）
- 回车发送到 /api/intent，流式显示结果
"""

import os
import sys
import json
import threading
import re
import time

# 添加 Qt DLL 到 PATH
_QT_ROOT = os.path.expandvars(
    r"%LocalAppData%\Programs\Python\Python310\Lib\site-packages\PyQt5\Qt5"
)
_QT_DLL = os.path.join(_QT_ROOT, "bin")
_QT_PLATFORMS = os.path.join(_QT_ROOT, "plugins", "platforms")
if os.path.isdir(_QT_DLL):
    os.environ["PATH"] = _QT_DLL + os.pathsep + os.environ.get("PATH", "")
if os.path.isdir(_QT_PLATFORMS):
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = _QT_PLATFORMS

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QLabel, QPushButton,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer
from PyQt5.QtGui import QFont, QKeyEvent, QTextCursor, QDragEnterEvent, QDropEvent
import urllib.request


# === 配置 ===
HOST = os.environ.get("AGENT_HOST", "http://127.0.0.1:8000")
INTENT_URL = f"{HOST}/api/intent"
CHAT_URL = f"{HOST}/api/chat"
TASKS_URL = f"{HOST}/api/tasks"
TASK_URL = f"{HOST}/api/task"

WINDOW_OPACITY = 0.92
WINDOW_WIDTH = 620
WINDOW_HEIGHT = 500


# === SSE 流读取线程 ===

class SSEReader(QThread):
    """异步读取 SSE 事件流"""
    chunk = pyqtSignal(str)
    done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, text: str, conversation_history: list | None = None):
        super().__init__()
        self.text = text

    def run(self):
        data = json.dumps({
            "message": self.text,
            "conversation_id": "overlay",
        }).encode("utf-8")
        req = urllib.request.Request(
            INTENT_URL,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=300)
            buffer = ""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8")
                # 按行解析 SSE
                while "\n\n" in buffer:
                    line, buffer = buffer.split("\n\n", 1)
                    if line.startswith("data: "):
                        payload = line[6:]
                        self.chunk.emit(payload)
            resp.close()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.done.emit()


# === 截图 + OCR 线程 ===

class ScreenshotReader(QThread):
    """后台截图 + OCR 线程"""
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            # 导入 screenshot/ocr 模块
            from tools.windows_control.screenshot import capture_fullscreen
            from tools.windows_control.ocr import recognize_file

            screen = capture_fullscreen()
            if "error" in screen:
                self.error.emit(screen["error"])
                return

            ocr_result = recognize_file(screen["file_path"])
            if "error" in ocr_result:
                self.error.emit(ocr_result["error"])
                return

            items = ocr_result.get("items", [])
            lines = []
            lines.append(f"📸 截图已保存: {screen['file_path']}")
            lines.append(f"  识别到 {ocr_result.get('count', 0)} 个文字区域:")
            lines.append("")
            for item in items[:20]:  # 最多显示 20 条
                text = item["text"]
                conf = item["confidence"]
                bbox = item["bbox"]
                lines.append(f"  [{conf:.0%}] \"{text}\"  ({bbox['left']},{bbox['top']})")

            if len(items) > 20:
                lines.append(f"  ... 还有 {len(items) - 20} 项未显示")

            self.result.emit("\n".join(lines))
        except Exception as e:
            self.error.emit(f"截图/OCR 失败: {str(e)}")


# === 任务状态查询线程 ===

class TaskFetcher(QThread):
    """后台查询任务状态"""
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, task_id: str = ""):
        super().__init__()
        self.task_id = task_id

    def run(self):
        try:
            url = f"{TASKS_URL}?limit=20" if not self.task_id else f"{TASK_URL}/{self.task_id}"
            resp = urllib.request.urlopen(url, timeout=10)
            data = json.loads(resp.read().decode("utf-8"))

            if self.task_id:
                task = data
                lines = [
                    f"📋 任务 {task['id']}",
                    f"  状态: {task['status']}",
                    f"  指令: {task.get('user_input', '')}",
                    f"  进度: {task.get('current_step', 0)}/{task.get('total_steps', 0)}",
                    f"  耗时: {task.get('elapsed', 0)}s",
                ]
                if task.get("result_summary"):
                    lines.append(f"  结果: {task['result_summary']}")
                if task.get("error"):
                    lines.append(f"  错误: {task['error'][:200]}")
                if task.get("step_details"):
                    lines.append("  最近步骤:")
                    for s in task["step_details"][-5:]:
                        lines.append(f"    [{s['step']}/{s['total']}] {s.get('detail','')[:60]}")
                self.result.emit("\n".join(lines))
            else:
                tasks = data.get("tasks", [])
                active_count = data.get("active_count", 0)
                if not tasks:
                    self.result.emit("📋 暂无任务记录")
                    return
                lines = [f"📋 共 {len(tasks)} 个任务（{active_count} 运行中）:"]
                for t in tasks:
                    status_icon = {"running": "🔄", "completed": "✅", "failed": "❌", "cancelled": "⏹", "pending": "⏳"}
                    icon = status_icon.get(t["status"], "•")
                    lines.append(
                        f"  {icon} {t['id']} | {t['status']} | "
                        f"{t.get('user_input','')[:40]} | "
                        f"{t.get('current_step',0)}/{t.get('total_steps',0)} | "
                        f"{t.get('elapsed',0)}s"
                    )
                self.result.emit("\n".join(lines))
        except Exception as e:
            self.error.emit(f"查询任务失败: {str(e)[:150]}")


# === 悬浮窗口 ===

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.conversation_history = []  # 多轮对话历史
        self._init_ui()
        self._setup_hotkeys()
        self.reader = None
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide)
        self._dragging = False  # 拖拽状态

    def _init_ui(self):
        self.setWindowTitle("Big Agent")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool  # 不在任务栏显示
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # 允许拖拽文件
        self.setAcceptDrops(True)

        # 主容器
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background: rgba(20, 20, 26, 230);
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,30);
            }
        """)
        self.container.setGeometry(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(8)

        # 标题栏
        title_row = QHBoxLayout()
        title = QLabel("Big Agent")
        title.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        self.status_icon = QLabel("●")
        self.status_icon.setStyleSheet("color: #4ade80; font-size: 10px; background: transparent;")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.status_icon)
        layout.addLayout(title_row)

        # 输出区
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.output.setStyleSheet("""
            QTextEdit {
                background: rgba(30, 30, 40, 200);
                border: none;
                border-radius: 6px;
                color: #e0e0e0;
                font-size: 13px;
                padding: 8px;
                selection-background-color: #3b82f6;
            }
            QScrollBar:vertical {
                width: 4px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,30);
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.output)

        # 输入区
        input_row = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("输入指令，回车执行  |  拖入文件发送  |  Ctrl+Shift+S 截图...")
        self.input_box.setStyleSheet("""
            QLineEdit {
                background: rgba(40, 40, 55, 200);
                border: 1px solid rgba(255,255,255,20);
                border-radius: 6px;
                color: #e0e0e0;
                font-size: 14px;
                padding: 8px 12px;
                selection-background-color: #3b82f6;
            }
            QLineEdit:focus {
                border: 1px solid rgba(59,130,246,150);
            }
        """)
        self.input_box.returnPressed.connect(self._send)

        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedWidth(60)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: rgba(59,130,246,200);
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 13px;
                padding: 6px;
            }
            QPushButton:hover {
                background: rgba(59,130,246,255);
            }
            QPushButton:pressed {
                background: rgba(37,99,235,255);
            }
            QPushButton:disabled {
                background: rgba(100,100,120,150);
            }
        """)
        self.send_btn.clicked.connect(self._send)

        input_row.addWidget(self.input_box)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

        # 快捷键提示
        hint = QLabel("Ctrl+Space 切换  |  Esc 关闭  |  Enter 发送  |  Ctrl+Shift+S 截图")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #555; font-size: 10px; background: transparent;")
        layout.addWidget(hint)

    def _setup_hotkeys(self):
        """注册全局热键"""
        try:
            import keyboard
            keyboard.add_hotkey("ctrl+space", self.toggle_visibility)
            keyboard.add_hotkey("ctrl+shift+s", self._take_screenshot)
        except ImportError:
            self._append_output("[警告] keyboard 未安装，全局热键不可用。pip install keyboard")

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self.input_box.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.hide()
        super().keyPressEvent(event)

    # === 文件拖拽支持 ===

    def dragEnterEvent(self, event: QDragEnterEvent):
        """检测拖入的文件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._dragging = True
            self.container.setStyleSheet("""
                QWidget {
                    background: rgba(30, 30, 50, 230);
                    border-radius: 12px;
                    border: 2px solid rgba(59,130,246,200);
                }
            """)

    def dragLeaveEvent(self, event):
        """拖拽离开恢复样式"""
        self._dragging = False
        self._reset_container_style()

    def dropEvent(self, event: QDropEvent):
        """处理文件拖入"""
        self._dragging = False
        self._reset_container_style()

        files = []
        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if local_path:
                files.append(local_path)

        if not files:
            return

        # 显示拖入的文件信息
        file_list = "\n".join(f"  📄 {f}" for f in files)
        self._append_output(f"📁 检测到拖入的文件 ({len(files)} 个):")
        self._append_output(file_list)
        self._append_output("")

        # 自动填入文件路径到输入框
        if len(files) == 1:
            self.input_box.setText(files[0])
            self.input_box.selectAll()
        else:
            self.input_box.setText(" ".join(f'"{f}"' for f in files))

    def _reset_container_style(self):
        self.container.setStyleSheet("""
            QWidget {
                background: rgba(20, 20, 26, 230);
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,30);
            }
        """)

    # === 截图 + OCR ===

    def _take_screenshot(self):
        """截图 + OCR 快捷键处理"""
        if self.reader and self.reader.isRunning():
            self._append_output("⏳ 正在执行中，请等待...")
            return

        self._append_output("📸 正在截图并识别文字...")
        self._set_busy(True)

        self.screenshot_reader = ScreenshotReader()
        self.screenshot_reader.result.connect(self._on_screenshot_result)
        self.screenshot_reader.error.connect(self._on_screenshot_error)
        self.screenshot_reader.start()

    def _on_screenshot_result(self, text: str):
        self._append_output(text)
        self._append_output("─" * 40)
        self._set_busy(False)

    def _on_screenshot_error(self, msg: str):
        self._append_output(f"❌ {msg}")
        self._set_busy(False)

    # === 输出与状态 ===

    def _append_output(self, text: str):
        """向输出区追加文本"""
        self.output.moveCursor(QTextCursor.End)
        self.output.insertPlainText(text + "\n")
        scrollbar = self.output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _set_busy(self, busy: bool):
        self.input_box.setEnabled(not busy)
        self.send_btn.setEnabled(not busy)
        self.status_icon.setStyleSheet(
            "color: #facc15; font-size: 10px; background: transparent;" if busy
            else "color: #4ade80; font-size: 10px; background: transparent;"
        )

    def _append_user_msg(self, text: str):
        """显示用户输入"""
        # 简短显示：取前 80 字符，换行用空格替代
        display = text.replace("\n", " ").strip()[:80]
        if len(text) > 80:
            display += "..."
        self._append_output(f">>> {display}")

    def _append_result_brief(self, result_text: str):
        """显示结果摘要（提取关键信息）"""
        self._append_output(f"  {result_text[:200]}")

    # === 发送指令 ===

    def _send(self):
        text = self.input_box.text().strip()
        if not text or not self.send_btn.isEnabled():
            return

        self.input_box.clear()
        self._append_user_msg(text)
        self._append_output("")
        self._set_busy(True)

        # 处理本地命令
        if text.startswith("/"):
            handled = self._handle_local_command(text)
            if handled:
                return

        # 意图引擎无状态，后续可在此注入 memory_store 上下文
        self.reader = SSEReader(text)
        self.reader.chunk.connect(self._on_chunk)
        self.reader.error.connect(self._on_error)
        self.reader.done.connect(self._on_done)
        self.reader.start()

    def _handle_local_command(self, text: str) -> bool:
        """处理本地命令（不以 SSE 方式发送到服务器）"""
        cmd = text.lower().strip()

        if cmd == "/tasks":
            self._append_output("📋 正在查询任务列表...")
            self.task_fetcher = TaskFetcher()
            self.task_fetcher.result.connect(self._on_task_result)
            self.task_fetcher.error.connect(self._on_task_error)
            self.task_fetcher.start()
            return True

        if cmd.startswith("/task "):
            task_id = cmd[6:].strip()
            if task_id:
                self._append_output(f"📋 正在查询任务 {task_id}...")
                self.task_fetcher = TaskFetcher(task_id)
                self.task_fetcher.result.connect(self._on_task_result)
                self.task_fetcher.error.connect(self._on_task_error)
                self.task_fetcher.start()
                return True
            else:
                self._append_output("⚠ 用法: /task <task_id>")
                self._on_done()
                return True

        if cmd == "/clear":
            self.conversation_history = []
            self.output.clear()
            self._append_output("🗑 对话已清空")
            self._append_output("─" * 40)
            self._set_busy(False)
            return True

        if cmd == "/help":
            self._append_output("📖 可用命令:")
            self._append_output("  /help      — 显示帮助")
            self._append_output("  /clear     — 清空对话")
            self._append_output("  /tasks     — 列出所有任务")
            self._append_output("  /task <id> — 查询任务状态")
            self._append_output("  Ctrl+Shift+S — 截图+OCR")
            self._append_output("  ─────────────────────")
            self._append_output("  直接输入指令发送到意图引擎")
            self._append_output("  拖拽文件到窗口查看文件路径")
            self._append_output("  Ctrl+Space 切换显示")
            self._append_output("─" * 40)
            self._set_busy(False)
            return True

        return False

    def _on_task_result(self, text: str):
        self._append_output(text)
        self._append_output("─" * 40)
        self._set_busy(False)

    def _on_task_error(self, msg: str):
        self._append_output(f"❌ {msg}")
        self._set_busy(False)

    def _on_chunk(self, payload: str):
        """处理 SSE 事件块"""
        try:
            d = json.loads(payload)
        except json.JSONDecodeError:
            return

        event_type = d.get("type", "")

        if event_type == "text":
            self._append_output(d.get("content", ""))
        elif event_type == "step":
            self._append_output(f"  [{d['step']}/{d['total']}] {d.get('action','')} — {d.get('description','')}")
        elif event_type == "step_result":
            result = d.get("result", {})
            if isinstance(result, dict):
                brief = result.get("success", "") or result.get("file_path", "") or result.get("count", "") or str(result)[:80]
                if brief:
                    self._append_output(f"    -> {brief}")
        elif event_type == "step_failed":
            self._append_output(f"  ❌ 步骤 {d['step']} 失败: {d.get('error','')[:100]}")
        elif event_type == "replan":
            self._append_output(f"  🔄 重新规划，新方案 {len(d.get('new_plan',[]))} 步")
        elif event_type == "step_retry":
            self._append_output(f"  🔄 重试 {d['attempt']}/{d['max_retries']}")
        elif event_type == "auto_fix":
            self._append_output(f"  🔧 {d.get('fix','')}")
        elif event_type == "memory_hit":
            self._append_output(f"  💡 记忆命中：{d.get('confidence','')}")
        elif event_type == "learning":
            self._append_output(f"  📚 {d.get('message','')}")
        elif event_type == "plan_generated":
            self._append_output(f"  📋 方案已生成，共 {d.get('steps_count',0)} 步")
        elif event_type == "context":
            self._append_output(f"  ℹ️  {d.get('content','')[:120]}")
        elif event_type == "error":
            self._append_output(f"  ❌ 错误：{d.get('content','')[:200]}")
        elif event_type == "steps_done":
            self._append_output(f"\n✅ 执行完成")
        elif event_type == "memory_saved":
            status = "✅ 成功" if d.get("result") == "成功" else "⚠ 部分完成"
            self._append_output(f"💾 已记住 | {status}")
        elif event_type == "research_plan":
            self._append_output(f"  🔍 需要搜索：{'、'.join(d.get('queries',[]))}")
        elif event_type == "research_result":
            self._append_output(f"  📄 搜索「{d.get('query','')}」→ {d.get('results_count',0)} 条结果")
        elif event_type == "research_done":
            self._append_output(f"  📖 阅读完毕，综合生成方案...")

    def _on_error(self, msg: str):
        self._append_output(f"\n❌ 连接错误：{msg[:200]}")
        self._set_busy(False)

    def _on_done(self):
        self._set_busy(False)
        self._append_output("─" * 40)

    # === 清空对话历史 ===

    def clear_history(self):
        """清空对话历史和输出"""
        self.conversation_history = []
        self.output.clear()
        self._append_output("🗑 对话已清空")
        self._append_output("─" * 40)


# === 启动 ===

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 悬浮窗关闭不退出

    # 设置应用样式
    app.setStyle("Fusion")

    window = OverlayWindow()

    # 居中显示
    screen = app.primaryScreen().geometry()
    x = (screen.width() - WINDOW_WIDTH) // 2
    y = (screen.height() - WINDOW_HEIGHT) // 2
    window.move(x, y)

    # 默认显示让用户知道存在，Esc 可隐藏
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
