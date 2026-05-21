"""Windows 控制工具集 — 鼠标、键盘、进程、窗口、截图、OCR"""
from tools.windows_control.mouse import (
    mouse_click, mouse_move, mouse_double_click, mouse_right_click,
    mouse_drag, mouse_scroll, mouse_position, get_screen_size,
)
from tools.windows_control.keyboard import (
    keyboard_type, keyboard_hotkey, keyboard_press, keyboard_write_enter,
    get_hotkey_list,
)
from tools.windows_control.process import (
    process_list, process_find, process_launch, process_kill, process_is_running,
)
from tools.windows_control.window import (
    window_list, window_find, window_activate, window_close,
    window_minimize, window_get_active,
)
from tools.windows_control.screenshot import (
    capture_fullscreen, capture_region, capture_active_window,
)
from tools.windows_control.ocr import (
    recognize_file, recognize_screen, recognize_region,
    recognize_active_window, find_text_on_screen, click_text_on_screen,
)
