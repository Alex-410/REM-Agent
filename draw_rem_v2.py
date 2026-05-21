"""
用 Pillow 从零绘制《Re:Zero》蕾姆（Rem） - 精修版
天蓝色短发 | 刘海遮右眼 | 浅蓝左眼 | 白色女仆装 + 蓝裙 | 蓝色发饰
"""

from PIL import Image, ImageDraw
import math

W, H = 600, 800
img = Image.new("RGB", (W, H), (235, 225, 215))  # 暖灰背景
draw = ImageDraw.Draw(img)

# ==================== 调色板 ====================
COLORS = {
    "skin":       (254, 228, 209),
    "skin_shade": (242, 213, 194),
    "skin_shadow":(230, 198, 178),
    "hair_main":  (72, 185, 225),    # 天蓝主色
    "hair_dark":  (52, 150, 205),    # 天蓝深色
    "hair_light": (130, 215, 245),   # 天蓝高光
    "hair_strand":(62, 168, 215),    # 发丝色
    "eye_white":  (255, 255, 255),
    "eye_iris":   (90, 195, 245),    # 浅蓝虹膜
    "eye_pupil":  (35, 65, 120),     # 深蓝瞳孔
    "eye_highlight": (255, 255, 255),
    "eye_line":   (25, 25, 35),
    "eyebrow":    (55, 120, 170),
    "blush":      (252, 196, 188),
    "lip":        (228, 155, 140),
    "lip_dark":   (210, 135, 120),
    "maid_white": (250, 248, 244),
    "maid_white_shade": (238, 235, 230),
    "maid_blue":  (65, 138, 205),    # 裙子主蓝
    "maid_blue_dark":  (45, 108, 178),
    "maid_blue_light": (100, 170, 225),
    "collar_blue":(55, 115, 190),
    "collar_trim":(75, 148, 215),
    "apron":      (252, 250, 247),
    "apron_shade":(240, 237, 233),
    "ribbon":     (85, 170, 228),    # 发饰蓝色
    "ribbon_dark":(60, 140, 200),
    "ribbon_core":(255, 238, 180),   # 花心金色
    "dress_trim": (240, 235, 225),
    "necklace":   (70, 148, 218),
}

C = COLORS

# ==================== 绘制 ====================

# ----- 1. 身体（背景层）-----

# 脖子
draw.rectangle([268, 310, 332, 360], fill=C["skin"])
draw.rectangle([272, 315, 328, 355], fill=C["skin_shade"])

# 肩膀和上身外轮廓 （白色女仆上衣）
draw.polygon([
    (145, 380),  # 左肩
    (180, 345),  # 左肩内
    (240, 330),  # 左领口
    (360, 330),  # 右领口
    (420, 345),  # 右肩内
    (455, 380),  # 右肩
    (470, 490),  # 右下
    (130, 490),  # 左下
], fill=C["maid_white"])

# 上衣阴影
draw.polygon([
    (145, 380), (180, 345), (200, 490), (130, 490)
], fill=C["maid_white_shade"])
draw.polygon([
    (470, 490), (420, 345), (400, 490), (455, 380)
], fill=C["maid_white_shade"])

# ----- 女仆领子 -----
# 蓝色V领
draw.polygon([
    (270, 328),
    (300, 380),
    (330, 328),
], fill=C["collar_blue"])

# V领白色边饰
draw.polygon([
    (260, 330),
    (270, 365),
    (278, 328),
    (300, 385),
    (322, 328),
    (330, 365),
    (340, 330),
    (300, 340),
], fill=C["maid_white"])

# V领蓝色外框线
draw.polygon([
    (255, 330),
    (268, 360),
    (275, 325),
    (300, 390),
    (325, 325),
    (332, 360),
    (345, 330),
], fill=None, outline=C["collar_trim"], width=2)

# 蓝色领结/系带
draw.polygon([
    (290, 368),
    (310, 368),
    (308, 420),
    (292, 420),
], fill=C["collar_blue"])

# 领结蝴蝶结
draw.polygon([
    (275, 365), (290, 360), (295, 375), (278, 378),
], fill=C["collar_blue"])
draw.polygon([
    (325, 365), (310, 360), (305, 375), (322, 378),
], fill=C["collar_blue"])
draw.ellipse([293, 367, 307, 375], fill=C["collar_trim"])

# ----- 白色围裙 -----
draw.polygon([
    (200, 410),
    (400, 410),
    (415, 550),
    (185, 550),
], fill=C["apron"])

# 围裙阴影（两侧）
draw.polygon([
    (200, 410), (230, 410), (215, 550), (185, 550)
], fill=C["apron_shade"])
draw.polygon([
    (400, 410), (370, 410), (385, 550), (415, 550)
], fill=C["apron_shade"])

# 围裙上缘装饰
draw.rectangle([200, 408, 400, 418], fill=C["maid_blue"])
draw.rectangle([200, 418, 400, 420], fill=C["maid_blue_dark"])

# 围裙肩带
draw.line([(200, 410), (175, 345)], fill=C["maid_white"], width=6)
draw.line([(400, 410), (425, 345)], fill=C["maid_white"], width=6)
draw.line([(200, 410), (175, 345)], fill=C["maid_white_shade"], width=2)
draw.line([(400, 410), (425, 345)], fill=C["maid_white_shade"], width=2)

# 围裙下方装饰花边（荷叶边效果）
for i in range(10):
    x_base = 190 + i * 24
    draw.arc([x_base, 540, x_base + 28, 560], 0, 180, fill=C["maid_white"], width=4)

# ----- 袖子（白色）-----
# 左袖
draw.polygon([
    (170, 350), (145, 380), (120, 430), (140, 445), (175, 430), (190, 380),
], fill=C["maid_white"])
draw.polygon([
    (145, 380), (120, 430), (140, 445), (150, 420),
], fill=C["maid_white_shade"])

# 右袖
draw.polygon([
    (430, 350), (455, 380), (480, 430), (460, 445), (425, 430), (410, 380),
], fill=C["maid_white"])
draw.polygon([
    (455, 380), (480, 430), (460, 445), (450, 420),
], fill=C["maid_white_shade"])

# ----- 蓝色裙子 -----
draw.polygon([
    (130, 490),
    (110, 590),
    (120, 660),
    (150, 700),
    (180, 730),
    (300, 745),
    (420, 730),
    (450, 700),
    (480, 660),
    (490, 590),
    (470, 490),
], fill=C["maid_blue"])

# 裙子阴影（两侧）
draw.polygon([
    (130, 490), (110, 590), (120, 660), (150, 700), (170, 700), (165, 490),
], fill=C["maid_blue_dark"])
draw.polygon([
    (470, 490), (490, 590), (480, 660), (450, 700), (430, 700), (435, 490),
], fill=C["maid_blue_dark"])

# 裙子褶皱
folds = [180, 220, 260, 300, 340, 380, 420]
for fx in folds:
    # 褶皱线（从上到下略微弯曲）
    start_y = 500
    end_y = 700 + (fx - 250) * 0.15
    points = []
    for t in range(11):
        ratio = t / 10
        y = start_y + ratio * (end_y - start_y)
        sway = math.sin(ratio * math.pi) * 12
        px = fx + sway * (1 if fx < 300 else -1)
        points.append((px, y))
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=C["maid_blue_dark"], width=2)

# 裙子底部花边（白色波浪边）
for i in range(15):
    x_base = 120 + i * 26
    draw.arc([x_base, 720, x_base + 30, 755], 0, 180, fill=C["dress_trim"], width=5)

# 裙子上的蓝色蝴蝶结装饰
bow_positions = [(250, 495), (300, 500), (350, 495)]
for bx, by in bow_positions:
    draw.polygon([(bx-10, by), (bx-2, by-3), (bx, by+2), (bx-7, by+5)], fill=C["maid_blue_light"])
    draw.polygon([(bx+10, by), (bx+2, by-3), (bx, by+2), (bx+7, by+5)], fill=C["maid_blue_light"])
    draw.ellipse([bx-2, by-1, bx+2, by+2], fill=C["ribbon_core"])


# ==================== 头部 ====================

# ----- 2. 脸部 -----
# 脸部椭圆（鹅蛋脸）
draw.ellipse([225, 133, 375, 305], fill=C["skin"])

# 脸部阴影 - 右侧
draw.chord([225, 133, 375, 305], 0, 90, fill=C["skin_shadow"])
# 下巴微调
draw.polygon([
    (230, 255),
    (222, 278),
    (228, 298),
    (245, 308),
    (255, 312),
    (300, 316),
    (345, 312),
    (355, 308),
    (372, 298),
    (378, 278),
    (370, 255),
], fill=C["skin"])

# ----- 3. 耳朵 -----
# 左耳（观众视角左侧）
draw.ellipse([215, 205, 232, 232], fill=C["skin"])
draw.ellipse([218, 208, 228, 228], fill=C["skin_shade"])
# 右耳
draw.ellipse([368, 205, 385, 232], fill=C["skin"])
draw.ellipse([372, 208, 382, 228], fill=C["skin_shade"])


# ==================== 头发 ====================

# ----- 4. 后发（底层）-----
draw.ellipse([208, 115, 392, 280], fill=C["hair_main"])
draw.polygon([
    (215, 130), (210, 200), (220, 270), (240, 300),
    (300, 310), (360, 300), (380, 270), (390, 200), (385, 130),
], fill=C["hair_main"])

# 后发阴影
draw.ellipse([215, 120, 385, 270], fill=C["hair_dark"])

# ----- 5. 刘海（覆盖右眼 - 观众左侧）-----

# 主刘海 - 覆盖右眼区域（观众左侧）
# 从头顶向左下倾斜覆盖
draw.polygon([
    (225, 120),
    (270, 120),
    (275, 145),
    (280, 175),
    (278, 210),
    (268, 238),
    (255, 248),
    (240, 245),
    (225, 238),
    (215, 220),
    (210, 195),
    (212, 155),
], fill=C["hair_main"])

# 刘海阴影
draw.polygon([
    (225, 120),
    (260, 120),
    (265, 145),
    (268, 170),
    (260, 200),
    (250, 220),
    (240, 218),
    (225, 210),
    (215, 195),
    (218, 155),
], fill=C["hair_dark"])

# 刘海高光
draw.line([(235, 125), (250, 160), (255, 190)], fill=C["hair_light"], width=2)
draw.line([(245, 125), (258, 155), (262, 180)], fill=C["hair_light"], width=2)

# 右侧刘海（露出左眼的右半边头发）
draw.polygon([
    (285, 120),
    (315, 120),
    (320, 145),
    (318, 165),
    (312, 175),
    (300, 168),
    (290, 158),
    (285, 145),
], fill=C["hair_main"])

draw.polygon([
    (288, 125),
    (310, 125),
    (314, 145),
    (312, 158),
    (302, 153),
    (292, 148),
], fill=C["hair_dark"])

# 头顶头发
draw.ellipse([220, 85, 380, 140], fill=C["hair_main"])
draw.ellipse([230, 90, 370, 135], fill=C["hair_dark"])

# 头顶高光
draw.arc([240, 92, 290, 125], 180, 360, fill=C["hair_light"], width=4)
draw.arc([300, 92, 350, 125], 180, 360, fill=C["hair_light"], width=3)

# ----- 6. 侧发（鬓角）-----

# 左鬓角（观众左侧）- 覆盖右耳
draw.polygon([
    (210, 140),
    (195, 170),
    (188, 200),
    (185, 230),
    (190, 255),
    (200, 268),
    (210, 262),
    (218, 240),
    (220, 200),
], fill=C["hair_main"])
draw.polygon([
    (208, 145),
    (195, 175),
    (190, 205),
    (188, 228),
    (195, 248),
    (202, 240),
    (210, 200),
], fill=C["hair_dark"])

# 右鬓角（观众右侧）
draw.polygon([
    (390, 140),
    (405, 170),
    (412, 200),
    (415, 230),
    (410, 255),
    (400, 268),
    (390, 262),
    (382, 240),
    (380, 200),
], fill=C["hair_main"])
draw.polygon([
    (392, 145),
    (405, 175),
    (410, 205),
    (412, 228),
    (405, 248),
    (398, 240),
    (390, 200),
], fill=C["hair_dark"])

# 发丝细节（左侧覆盖右眼的头发）
for i in range(6):
    x_start = 218 + i * 8
    draw.line([
        (x_start, 130 + i * 3),
        (x_start + 5 + i, 180 + i * 5),
        (x_start + 3 + i, 220 + i * 4),
    ], fill=C["hair_strand"], width=2)

# 右侧发丝细节
for i in range(4):
    x_start = 390 - i * 8
    draw.line([
        (x_start, 140 + i * 5),
        (x_start - 5, 190 + i * 5),
    ], fill=C["hair_strand"], width=2)

# ----- 7. 脖子处的头发（发尾）-----
draw.polygon([
    (230, 270),
    (225, 295),
    (230, 318),
    (245, 325),
    (260, 328),
    (280, 335),
    (300, 340),
    (320, 335),
    (340, 328),
    (355, 325),
    (370, 318),
    (375, 295),
    (370, 270),
], fill=C["hair_main"])

# 发尾阴影
draw.polygon([
    (235, 280),
    (228, 300),
    (235, 315),
    (250, 322),
    (270, 325),
    (240, 310),
], fill=C["hair_dark"])
draw.polygon([
    (365, 280),
    (372, 300),
    (365, 315),
    (350, 322),
    (330, 325),
    (360, 310),
], fill=C["hair_dark"])

# 发尾细节
for x in range(240, 365, 12):
    draw.line([(x, 290), (x + 2, 330)], fill=C["hair_strand"], width=1)


# ==================== 面部细节 ====================

# ----- 8. 眉毛 -----

# 左眉（观众左侧 - 被头发遮住的右眼上方，隐约可见）
draw.arc([252, 188, 278, 200], 180, 360, fill=C["eyebrow"], width=2)

# 右眉（观众右侧 - 可见左眼上方）
draw.arc([318, 188, 348, 200], 180, 360, fill=C["eyebrow"], width=3)


# ----- 9. 眼睛 -----

# 右眼（观众左侧 - 被刘海遮住，只露出一条缝）
draw.arc([258, 203, 282, 218], 180, 360, fill=C["eye_line"], width=2)

# *** 左眼（观众右侧 - 唯一完全可见） ***
eye_center_x = 335
eye_center_y = 210

# 眼白
draw.ellipse([320, 200, 352, 222], fill=C["eye_white"])

# 上眼睑（粗线，带眼角上挑 -  anime风格）
draw.arc([316, 196, 356, 218], 180, 360, fill=C["eye_line"], width=3)
# 眼角延长线（眼尾上挑）
draw.line([(352, 200), (360, 196)], fill=C["eye_line"], width=2)

# 下眼睑
draw.arc([320, 210, 352, 226], 0, 180, fill=C["eye_line"], width=1)

# 虹膜 - 浅蓝色
draw.ellipse([328, 204, 344, 220], fill=C["eye_iris"])

# 虹膜渐变（上深下浅）
draw.ellipse([330, 205, 342, 214], fill=C["eye_pupil"])

# 瞳孔（深色圆点）
draw.ellipse([334, 209, 340, 215], fill=C["eye_pupil"])

# 高光 - 大高光
draw.ellipse([336, 206, 342, 212], fill=C["eye_highlight"])

# 高光 - 小高光（左下）
draw.ellipse([330, 213, 334, 217], fill=C["eye_highlight"])

# 上睫毛
draw.line([(318, 199), (324, 196)], fill=C["eye_line"], width=2)
draw.line([(322, 197), (330, 195)], fill=C["eye_line"], width=2)
# 下睫毛
draw.line([(325, 221), (330, 222)], fill=C["eye_line"], width=1)
draw.line([(348, 220), (352, 221)], fill=C["eye_line"], width=1)

# 眼睛下方的卧蚕
draw.arc([320, 220, 352, 232], 0, 180, fill=C["blush"], width=2)

# ----- 10. 腮红 -----
draw.ellipse([240, 245, 260, 262], fill=C["blush"])
draw.ellipse([345, 245, 365, 262], fill=C["blush"])

# 腮红模糊效果（三层叠加）
for i in range(3):
    alpha = 0.4 - i * 0.12
    r, g, b = C["blush"]
    color = (int(r * alpha + 254 * (1-alpha)), int(g * alpha + 228 * (1-alpha)), int(b * alpha + 209 * (1-alpha)))
    offset = i * 4
    draw.ellipse([238 - offset, 243 - offset, 262 + offset, 264 + offset], fill=color)

for i in range(3):
    alpha = 0.4 - i * 0.12
    r, g, b = C["blush"]
    color = (int(r * alpha + 254 * (1-alpha)), int(g * alpha + 228 * (1-alpha)), int(b * alpha + 209 * (1-alpha)))
    offset = i * 4
    draw.ellipse([343 - offset, 243 - offset, 367 + offset, 264 + offset], fill=color)


# ----- 11. 鼻子（小巧，动漫风格）-----
# 淡淡的小点表示鼻子
draw.line([(300, 228), (300, 236)], fill=C["skin_shadow"], width=2)

# ----- 12. 嘴巴 -----

# 微笑的嘴
draw.arc([282, 262, 310, 274], 180, 360, fill=C["lip"], width=2)

# 下唇
draw.arc([284, 267, 308, 278], 0, 180, fill=C["lip_dark"], width=2)

# 嘴角
draw.line([(280, 267), (282, 267)], fill=C["lip_dark"], width=1)
draw.line([(310, 267), (312, 267)], fill=C["lip_dark"], width=1)

# 下唇阴影
draw.arc([286, 272, 306, 280], 0, 180, fill=C["skin_shade"], width=1)


# ==================== 发饰 ====================

# ----- 13. 蓝色花朵发饰（观众右侧）-----
fx, fy = 390, 145

# 花朵 - 6片花瓣
petal_offsets = [
    (0, -14), (12, -7), (12, 7),
    (0, 14), (-12, 7), (-12, -7),
]
for dx, dy in petal_offsets:
    draw.ellipse([fx+dx-8, fy+dy-8, fx+dx+8, fy+dy+8], fill=C["ribbon"])

# 花瓣阴影
for dx, dy in petal_offsets[::2]:
    draw.ellipse([fx+dx-6, fy+dy-6, fx+dx+6, fy+dy+6], fill=C["ribbon_dark"])

# 花心
draw.ellipse([fx-6, fy-6, fx+6, fy+6], fill=C["ribbon_core"])
draw.ellipse([fx-3, fy-3, fx+3, fy+3], fill=(255, 248, 210))

# 花瓣高光
for dx, dy in petal_offsets[:3]:
    draw.ellipse([fx+dx-3, fy+dy-5, fx+dx+1, fy+dy-1], fill=(180, 215, 245))

# 发饰飘带（从花朵垂下）
draw.polygon([
    (fx+5, fy+12),
    (fx+18, fy+28),
    (fx+12, fy+35),
    (fx+2, fy+18),
], fill=C["ribbon"])

draw.polygon([
    (fx-5, fy+12),
    (fx-18, fy+28),
    (fx-12, fy+35),
    (fx-2, fy+18),
], fill=C["ribbon"])

# 飘带阴影
draw.polygon([
    (fx+5, fy+15),
    (fx+15, fy+28),
    (fx+12, fy+32),
], fill=C["ribbon_dark"])
draw.polygon([
    (fx-5, fy+15),
    (fx-15, fy+28),
    (fx-12, fy+32),
], fill=C["ribbon_dark"])

# 飘带末端分叉
draw.line([(fx+18, fy+28), (fx+22, fy+38)], fill=C["ribbon"], width=3)
draw.line([(fx+12, fy+35), (fx+10, fy+42)], fill=C["ribbon"], width=2)
draw.line([(fx-18, fy+28), (fx-22, fy+38)], fill=C["ribbon"], width=3)
draw.line([(fx-12, fy+35), (fx-10, fy+42)], fill=C["ribbon"], width=2)


# ==================== 最终细节 ====================

# 脖子上的阴影（下巴下方）
draw.arc([258, 305, 342, 330], 0, 180, fill=C["skin_shadow"], width=3)

# 锁骨线
draw.line([(225, 345), (255, 350)], fill=C["skin_shade"], width=1)
draw.line([(345, 350), (375, 345)], fill=C["skin_shade"], width=1)

# 保存
img.save("output/rem_final.png")
print(f"OK 蕾姆精修版已保存到 output/rem_final.png")
print(f"   尺寸: {W}x{H}")
