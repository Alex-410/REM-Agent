---
name: image-generation
description: 用 Python Pillow 生成图像：绘制图表、生成验证码、制作表情包、合成图片。
---

# image-generation

## Overview

本技能介绍如何使用 Python 的 Pillow 库进行图像生成，涵盖基础绘图、图表生成、验证码制作、表情包合成以及图片合成等常见应用场景。Pillow 是 Python 中功能丰富的图像处理库，支持多种图像格式，提供丰富的绘图和图像操作 API，适合快速开发图像生成工具。

## When to Use

- 需要生成简单的数据可视化图表（如折线图、柱状图）而无需引入 matplotlib 等重量级库时。
- 需要动态生成验证码图片用于网站或应用的安全验证。
- 需要将多张图片或文字合成到一张图片上制作表情包、海报、水印等。
- 需要批量化处理或生成图片，如自动生成缩略图、拼接图片等。
- 在服务器端或脚本中需要程序化创建图像资源。

## Process

1. **环境准备**
   - 安装 Pillow：`pip install Pillow`
   - 导入相关模块：`from PIL import Image, ImageDraw, ImageFont, ImageFilter`

2. **创建或加载图像**
   - 创建一个空白图像：`Image.new('RGB', (width, height), color)`
   - 打开现有图像：`Image.open('image.jpg')`

3. **绘图操作（ImageDraw）**
   - 创建 Draw 对象：`draw = ImageDraw.Draw(image)`
   - 绘制形状：`draw.rectangle()`, `draw.ellipse()`, `draw.line()`, `draw.polygon()` 等
   - 绘制文本：`draw.text(position, text, fill, font)`

4. **生成图表**
   - 绘制坐标轴和刻度
   - 根据数据点绘制折线或柱状（使用矩形或线条）
   - 添加标题和标签

5. **生成验证码**
   - 创建指定大小的空白图像
   - 随机生成四位字母数字组合
   - 绘制干扰点、干扰线、扭曲效果
   - 将验证码文本渲染到图像上

6. **制作表情包**
   - 加载基础图片（如模板表情图）
   - 使用 `ImageDraw.text` 添加文字，并设置合适的字体大小、颜色、描边
   - 可添加滤镜（如模糊、浮雕）增加趣味

7. **合成图片**
   - 使用 `paste()` 方法将一个图像粘贴到另一个图像的指定位置
   - 支持透明度处理（`paste()` 时传入 mask 参数）
   - 调整大小（`resize()`）后拼合

8. **保存或展示**
   - 保存：`image.save('output.png')` （支持多种格式）
   - 展示（仅开发环境）：`image.show()`

## Verification

- 生成的图片文件可正常打开，且内容符合预期（图表比例正确、验证码可识别、文字位置准确）。
- 图像尺寸、颜色模式（RGB/RGBA）正确，无异常色偏或变形。
- 对于验证码，应确保足够随机且难以被机器自动识别（添加适当噪点、扭曲）。
- 表情包文字清晰，无溢出边界，与原图风格协调。
- 合成图片各图层位置、透明度符合设计要求，无锯齿或残留像素。
- 可编写单元测试，对关键函数（如绘图函数、验证码生成函数）进行结果验证（如比对像素值或 MD5 摘要）。