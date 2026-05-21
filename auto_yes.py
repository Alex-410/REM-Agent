"""
自动点"确定/Yes/Allow"按钮 — 减少 Claude Code 权限确认的频繁点击

使用方法：
  python auto_yes.py                  # 启动监控（默认每 2 秒检测一次）
  python auto_yes.py --rate 1         # 每秒检测一次
  python auto_yes.py --debug          # 保存截图方便调试

原理：每隔 N 秒截一次屏幕 → OCR 识别按钮文本 → 找到就点

关闭：按 Ctrl+C

安装依赖（以 Windows 为例）：
  1. pip install pyautogui pytesseract pillow keyboard
  2. 下载 Tesseract OCR:
     https://github.com/UB-Mannheim/tesseract/wiki
     安装后把路径改到下面 TESSERACT_CMD
"""

import argparse
import time
import sys

# ===== 配置 =====
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# 要识别的按钮文本（中英文）
KEYWORDS = [
    "yes", "approve", "allow", "确定", "允许", "y", "approval",
    "是", "确认",
]

try:
    import pyautogui
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
except ImportError:
    print("=" * 60)
    print("缺少依赖，一键安装：")
    print()
    print("  pip install pyautogui pytesseract pillow")
    print()
    print("还需要 Tesseract OCR 引擎：")
    print("  https://github.com/UB-Mannheim/tesseract/wiki")
    print("  安装后把上面 TESSERACT_CMD 改成你的路径")
    print("=" * 60)
    sys.exit(1)


def find_and_click(debug: bool = False) -> bool:
    """截图 → OCR → 找按钮 → 点击。返回是否点了东西。"""
    w, h = pyautogui.size()

    # 只检测屏幕下半部分（按钮基本都在底部）
    region = (0, int(h * 0.55), w, int(h * 0.45))

    screenshot = pyautogui.screenshot(region=region)

    if debug:
        screenshot.save("_yes_debug.png")

    data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)

    for i in range(len(data["text"])):
        text = (data["text"][i] or "").strip().lower()
        if not text:
            continue

        matched = False
        for kw in KEYWORDS:
            if kw == text or text.startswith(kw) or kw.startswith(text):
                matched = True
                break

        if not matched:
            continue

        x = data["left"][i] + region[0]
        y = data["top"][i] + region[1]
        w2 = data["width"][i]
        h2 = data["height"][i]

        cx = x + w2 // 2
        cy = y + h2 // 2 + 10

        print(f"[auto_yes] 检测到 '{data['text'][i]}' → 点击 ({cx},{cy})")
        pyautogui.click(cx, cy)
        time.sleep(0.5)
        return True

    return False


def main():
    parser = argparse.ArgumentParser(description="自动点 Yes 按钮")
    parser.add_argument("--rate", type=float, default=2.0, help="检测间隔秒数")
    parser.add_argument("--debug", action="store_true", help="保存调试截图")
    args = parser.parse_args()

    print(f"[auto_yes] 启动 (间隔 {args.rate}s, debug={args.debug})")
    print("[auto_yes] 按 Ctrl+C 停止")
    print()

    count = 0
    try:
        while True:
            try:
                if find_and_click(debug=args.debug):
                    count += 1
                    print(f"[auto_yes] 已自动点击 {count} 次")
            except Exception as e:
                print(f"[auto_yes] 出错: {e}")

            time.sleep(args.rate)
    except KeyboardInterrupt:
        print(f"\n[auto_yes] 停止，共点击 {count} 次")


if __name__ == "__main__":
    main()
