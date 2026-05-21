---
name: windows-automation
description: Windows 桌面自动化：窗口操作、鼠标键盘、OCR 识别、截图。用于控制微信、QQ、浏览器等桌面应用。
---

# windows-automation

## Overview
Windows桌面自动化技能提供了一套完整的工具和方法，用于在没有UI自动化接口的情况下，通过模拟用户操作（鼠标点击、键盘输入）和图像识别（OCR、截图）来控制Windows桌面应用程序。适用于传统Win32应用、WPF、Qt等常见桌面框架，以及无法通过标准API自动化的场景。

## When to Use
- 需要批量处理微信、QQ消息，自动回复或发送文件。
- 需要自动操作浏览器（如IE、Edge、Chrome等）但无法使用Selenium或WebDriver时。
- 需要将老旧桌面应用（如企业ERP、财务软件）集成到自动化流程中。
- 需要对桌面进行图像识别（如捕获区域文字、识别动态验证码）。
- 需要监控或录制桌面应用状态，进行异常检测。

## Process
1. **环境准备**：安装Python和必要的库（如`pyautogui`、`opencv-python`、`pytesseract`、`pywin32`、`uiautomation`等）。
2. **窗口定位**：使用`pywin32`或`uiautomation`找到目标窗口句柄，获取窗口位置、大小、标题。
3. **鼠标键盘操作**：
   - 移动鼠标：`pyautogui.moveTo(x, y, duration)`
   - 点击：`pyautogui.click(x, y)`
   - 键盘输入：`pyautogui.typewrite('text')` 或组合键 `pyautogui.hotkey('ctrl', 'c')`
4. **截图与OCR识别**：
   - 区域截图：`pyautogui.screenshot(region=(x, y, w, h))`
   - OCR文字识别：利用`pytesseract`或`Windows.Media.Ocr`提取区域文字。
5. **流程控制**：结合条件判断和循环，实现复杂的自动化逻辑（如等待元素出现、重试机制）。
6. **错误处理**：添加超时和异常捕获，防止自动化中断。

## Verification
- **单元测试**：验证单个操作（如点击坐标是否正确、窗口是否激活）符合预期。
- **集成测试**：运行完整的自动化脚本，检查最终结果（如消息是否发送、文件是否下载）。
- **图像比对**：通过截图与预期模板对比，确认UI状态正确。
- **日志记录**：输出操作步骤、截图和OCR结果，便于回溯问题。
- **稳定性验证**：在多轮重复测试中观察是否出现定位失败、响应超时等问题。