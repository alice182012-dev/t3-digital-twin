"""Render a text file as a dark terminal-style PNG with a caption line. Usage: render_output.py TEXT PNG CAPTION"""
import sys
from PIL import Image, ImageDraw, ImageFont

text, png, caption = sys.argv[1:4]
lines = open(text).read().rstrip("\n").split("\n")
font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 13)
step = 19
width = max(int(font.getlength(l)) for l in lines + [caption]) + 40
height = step * (len(lines) + 3) + 30
image = Image.new("RGB", (max(width, 900), height), (14, 24, 41))
draw = ImageDraw.Draw(image)
y = 18
for line in lines:
    draw.text((18, y), line, font=font, fill=(226, 232, 240))
    y += step
y += 4
draw.line([(18, y), (image.width - 18, y)], fill=(71, 85, 105))
draw.text((18, y + 8), caption, font=font, fill=(148, 163, 184))
image.save(png)
