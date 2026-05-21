"""
用 Pillow 从零绘制《Re:Zero》蕾姆（Rem）
- 天蓝色短发，刘海遮右眼
- 浅蓝色左瞳孔
- 白色女仆装 + 天蓝色裙子
- 蓝色发饰
"""

from PIL import Image, ImageDraw
import math

# ===== 尺寸设置 =====
W, H = 500, 700
img = Image.new("RGB", (W, H), (240, 235, 230))  # 暖灰背景
draw = ImageDraw.Draw(img)

# ===== 颜色定义 =====
SKIN       = (255, 224, 204)
SKIN_SHADOW = (245, 210, 190)
HAIR_BLUE  = (80, 180, 220)      # 天蓝色
HAIR_DARK  = (60, 150, 200)      # 深天蓝
HAIR_HIGHLIGHT = (140, 210, 240) # 高光
WHITE      = (255, 255, 255)
EYE_BLUE   = (100, 190, 240)     # 浅蓝瞳孔
EYE_DARK   = (40, 80, 140)       # 深蓝
MAID_WHITE = (248, 246, 242)
MAID_BLUE  = (70, 140, 200)      # 裙子蓝色
MAID_BLUE_DARK = (50, 110, 170)
RIBBON     = (90, 170, 220)      # 发饰蓝
RIBBON_ACCENT = (60, 140, 200)
LIP        = (220, 140, 130)
COLLAR_BLUE = (60, 120, 190)
BLUSH      = (255, 200, 190)

# ===== 坐标参考 =====
# 头部中心: (250, 200)
# 身体: 从脖子往下到约 650

# ----- 1. 画身体 (先画后面层) -----

# 脖子
draw.rectangle([230, 265, 270, 310], fill=SKIN)

# ----- 白色女仆上衣 (身体躯干) -----
# 上身轮廓
body_top_y = 290
body_bottom_y = 420
draw.polygon([
    (180, body_top_y),
    (160, body_bottom_y),
    (340, body_bottom_y),
    (320, body_top_y),
], fill=MAID_WHITE)

# 女仆领子 - 蓝色V领装饰
draw.polygon([
    (235, 275),
    (250, 310),
    (265, 275),
], fill=COLLAR_BLUE)

# 领口白色部分
draw.polygon([
    (220, 278),
    (235, 305),
    (250, 275),
    (265, 305),
    (280, 278),
    (250, 290),
], fill=WHITE)

# 蓝色领带/系带
draw.polygon([
    (245, 290),
    (255, 290),
    (252, 340),
    (248, 340),
], fill=COLLAR_BLUE)

# 白色围裙
draw.polygon([
    (195, 360),
    (305, 360),
    (315, 465),
    (185, 465),
], fill=WHITE, outline=(230, 228, 225))

# 围裙上方装饰线
draw.rectangle([198, 360, 302, 368], fill=(230, 228, 225))

# 围裙肩带
draw.line([(195, 360), (180, 295)], fill=WHITE, width=4)
draw.line([(305, 360), (320, 295)], fill=WHITE, width=4)

# 袖子上臂 (白色)
draw.ellipse([155, 310, 195, 370], fill=MAID_WHITE)
draw.ellipse([305, 310, 345, 370], fill=MAID_WHITE)

# ----- 天蓝色裙子 -----
draw.polygon([
    (160, 420),
    (145, 520),
    (155, 580),
    (185, 620),
    (315, 620),
    (345, 580),
    (355, 520),
    (340, 420),
], fill=MAID_BLUE)

# 裙子褶皱 - 深色线条
for x in range(180, 330, 25):
    draw.line([(x, 440), (x - 10 + (x-180)//5, 610)], fill=MAID_BLUE_DARK, width=2)

# 裙子底部白色花边
draw.arc([170, 605, 330, 640], 0, 180, fill=WHITE, width=6)

# ----- 2. 画头部 -----

# 脸型 - 椭圆
face_bbox = [195, 120, 305, 260]  # 110x140
draw.ellipse(face_bbox, fill=SKIN)

# 下巴 - 用多边形微调下巴形状
draw.polygon([
    (200, 210),
    (195, 230),
    (205, 250),
    (220, 260),
    (250, 265),
    (280, 260),
    (295, 250),
    (305, 230),
    (300, 210),
], fill=SKIN)

# ----- 3. 画耳朵 -----
# 左耳 (从观众视角)
draw.ellipse([188, 175, 200, 198], fill=SKIN_SHADOW)
# 右耳
draw.ellipse([300, 175, 312, 198], fill=SKIN_SHADOW)

# ----- 4. 画刘海（右眼被遮住，观众视角左侧）-----

# 右侧刘海（观众右侧，露出左眼）
# 先画覆盖在脸上的头发
# 这是覆盖右眼（观众左侧）的部分
fringe_right_eye = [
    (195, 118),   # 头顶左
    (245, 118),   # 头顶中
    (250, 165),   # 垂下来遮到眼睛位置
    (245, 205),   # 遮到脸颊
    (225, 210),
    (210, 205),
    (195, 190),
    (185, 155),
]
draw.polygon(fringe_right_eye, fill=HAIR_BLUE)

# 右侧刘海（露出左眼）的头发分线 - 向右边梳
fringe_left_side = [
    (245, 118),
    (265, 118),
    (275, 145),
    (270, 165),
    (260, 155),
    (250, 148),
]
draw.polygon(fringe_left_side, fill=HAIR_BLUE)

# 更精细的刘海层次 - 覆盖右眼区域的发丝
hair_strands = [
    # 几条弧线模拟发丝
    [(195, 120), (210, 170), (215, 195)],
    [(205, 120), (220, 168), (225, 200)],
    [(215, 118), (230, 165), (235, 202)],
    [(225, 118), (240, 160), (242, 198)],
]
for strand in hair_strands:
    draw.line(strand, fill=HAIR_DARK, width=3)

# 右侧（观众左侧）头发的加深阴影
draw.polygon([
    (195, 130), (210, 160), (215, 190), (205, 190), (195, 170)
], fill=HAIR_DARK)

# ----- 5. 画主头发（头顶和后脑）-----

# 头顶头发
draw.ellipse([185, 80, 315, 140], fill=HAIR_BLUE)
# 头顶阴影
draw.ellipse([195, 85, 305, 130], fill=HAIR_DARK)

# 侧发 - 左（观众视角）
draw.ellipse([170, 110, 200, 200], fill=HAIR_BLUE)
draw.ellipse([165, 115, 195, 190], fill=HAIR_DARK)

# 侧发 - 右（观众视角）
draw.ellipse([300, 110, 330, 200], fill=HAIR_BLUE)
draw.ellipse([305, 115, 335, 190], fill=HAIR_DARK)

# 鬓角发丝 - 左
draw.line([(175, 140), (185, 195), (190, 210)], fill=HAIR_DARK, width=2)
draw.line([(180, 135), (190, 190), (195, 205)], fill=HAIR_BLUE, width=2)

# 鬓角发丝 - 右
draw.line([(325, 140), (315, 195), (310, 210)], fill=HAIR_DARK, width=2)
draw.line([(320, 135), (310, 190), (305, 205)], fill=HAIR_BLUE, width=2)

# 头发高光
draw.arc([200, 90, 240, 130], 180, 360, fill=HAIR_HIGHLIGHT, width=3)
draw.arc([260, 90, 300, 130], 180, 360, fill=HAIR_HIGHLIGHT, width=3)

# ----- 6. 画眉毛 -----

# 左眉（观众右侧 - 可见左眼上方）
draw.arc([220, 160, 245, 175], 180, 360, fill=HAIR_DARK, width=3)
# 右眉（观众左侧 - 被头发遮住大部分）
draw.arc([255, 160, 280, 175], 180, 360, fill=HAIR_DARK, width=2)

# ----- 7. 画左眼（观众右侧 - 唯一可见眼睛）-----

# 眼白
draw.ellipse([218, 180, 248, 198], fill=WHITE)

# 上眼线
draw.arc([215, 177, 250, 195], 180, 360, fill=(30, 30, 40), width=2)

# 下眼线
draw.arc([218, 185, 248, 200], 0, 180, fill=(30, 30, 40), width=1)

# 瞳孔 - 浅蓝色
draw.ellipse([226, 185, 240, 198], fill=EYE_BLUE)

# 瞳孔高光
draw.ellipse([230, 187, 236, 193], fill=WHITE)

# 瞳孔中的深色
draw.ellipse([230, 189, 236, 195], fill=EYE_DARK)

# 上睫毛
draw.line([(215, 180), (222, 178)], fill=(30, 30, 40), width=2)
draw.line([(218, 179), (228, 177)], fill=(30, 30, 40), width=2)

# 下睫毛
draw.line([(220, 198), (226, 199)], fill=(30, 30, 40), width=1)

# 在眼睛下方的卧蚕/阴影
draw.arc([218, 198, 248, 210], 0, 180, fill=BLUSH, width=2)

# ----- 8. 画右眼（观众左侧 - 被刘海遮住，只露出一点点）-----
# 微微露出一丝右眼轮廓
draw.arc([252, 180, 278, 196], 180, 360, fill=(30, 30, 40), width=1)

# ----- 9. 画腮红 -----
draw.ellipse([200, 207, 218, 222], fill=BLUSH)
draw.ellipse([282, 207, 300, 222], fill=BLUSH)

# ----- 10. 画嘴巴 -----

# 上唇 - 小弧线（温柔的微笑）
draw.arc([238, 233, 258, 243], 0, 180, fill=LIP, width=2)

# 下唇
draw.arc([240, 238, 260, 248], 180, 360, fill=LIP, width=2)

# 嘴角微微上扬
draw.line([(236, 237), (240, 238)], fill=LIP, width=1)
draw.line([(260, 238), (264, 237)], fill=LIP, width=1)

# ----- 11. 画蓝色发饰（右侧头发上，观众右侧）-----

# 花朵形状发饰 - 在头的右侧（观众视角右侧）
flower_x, flower_y = 310, 130

# 花瓣 - 用椭圆拼成花朵
petals_pos = [
    (flower_x, flower_y - 12),
    (flower_x + 10, flower_y - 6),
    (flower_x + 10, flower_y + 6),
    (flower_x, flower_y + 12),
    (flower_x - 10, flower_y + 6),
    (flower_x - 10, flower_y - 6),
]
for px, py in petals_pos:
    draw.ellipse([px-7, py-7, px+7, py+7], fill=RIBBON)

# 花心
draw.ellipse([flower_x-5, flower_y-5, flower_x+5, flower_y+5], fill=(255, 240, 180))

# 发饰的带子/飘带
draw.polygon([
    (flower_x+8, flower_y+8),
    (flower_x+20, flower_y+20),
    (flower_x+15, flower_y+25),
    (flower_x+5, flower_y+12),
], fill=RIBBON)

draw.polygon([
    (flower_x-8, flower_y+8),
    (flower_x-20, flower_y+20),
    (flower_x-15, flower_y+25),
    (flower_x-5, flower_y+12),
], fill=RIBBON)

# ----- 12. 头发底部（脖子处）-----

# 脖子后的头发
draw.ellipse([210, 240, 290, 300], fill=HAIR_BLUE)

# 头发末端层次感
draw.polygon([
    (205, 250),
    (210, 280),
    (220, 290),
    (235, 295),
    (250, 290),
    (265, 295),
    (280, 290),
    (290, 280),
    (295, 250),
], fill=HAIR_DARK)

# 发丝细节
for x in range(215, 290, 12):
    draw.line([(x, 255), (x + 3, 288)], fill=(60, 155, 205), width=1)

# ----- 13. 衣服细节补充 -----

# 白色围裙的花边装饰
draw.arc([190, 455, 310, 475], 0, 180, fill=(235, 233, 230), width=3)

# 裙子上的蓝色蝴蝶结装饰
bow_x, bow_y = 250, 425
draw.polygon([
    (bow_x-12, bow_y), (bow_x-3, bow_y-3), (bow_x, bow_y+2), (bow_x-8, bow_y+5)
], fill=RIBBON_ACCENT)
draw.polygon([
    (bow_x+12, bow_y), (bow_x+3, bow_y-3), (bow_x, bow_y+2), (bow_x+8, bow_y+5)
], fill=RIBBON_ACCENT)
draw.ellipse([bow_x-3, bow_y-1, bow_x+3, bow_y+3], fill=(255, 240, 200))

# 保存
img.save("output/rem_final.png")
print("✅ 蕾姆画像已保存到 output/rem_final.png")
print(f"   尺寸: {W}x{H}")
