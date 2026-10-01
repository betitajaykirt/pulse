"""Document-style context data-flow diagram for PULSE."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1800, 1240
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
INK = (17, 17, 17)

body = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 22)
flow = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 16)
title = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 32)
box_font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 20)
sub_font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 16)
proc_font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 18)


def size(text, font):
    b = d.textbbox((0, 0), text, font=font)
    return b[2] - b[0], b[3] - b[1]


def center(text, cx, cy, font):
    w, h = size(text, font)
    d.text((cx - w / 2, cy - h / 2 - 1), text, font=font, fill=INK)


def label(text, x1, x2, y):
    w, h = size(text, flow)
    tx = (x1 + x2) / 2 - w / 2
    ty = y - h - 5
    d.rectangle((tx - 3, ty - 1, tx + w + 3, ty + h + 1), fill="white")
    d.text((tx, ty), text, font=flow, fill=INK)


def head(x, y, direction):
    s = 8
    if direction == "down":
        d.polygon([(x, y), (x - s, y - 13), (x + s, y - 13)], fill=INK)
    elif direction == "up":
        d.polygon([(x, y), (x - s, y + 13), (x + s, y + 13)], fill=INK)


def stroke(pts):
    d.line(pts, fill=INK, width=2)


def entity(box, lines, fonts):
    x, y, w, h = box
    d.rectangle((x, y, x + w, y + h), outline=INK, width=2)
    heights = [size(t, f)[1] for t, f in zip(lines, fonts)]
    block = sum(heights) + 5 * (len(lines) - 1)
    cy = y + (h - block) / 2
    for text, font, th in zip(lines, fonts, heights):
        tw, _ = size(text, font)
        d.text((x + (w - tw) / 2, cy), text, font=font, fill=INK)
        cy += th + 5


d.line((36, 26, 1764, 26), fill=INK, width=2)
d.text((44, 40), "Data Flow Diagram", font=title, fill=INK)
for i, row in enumerate([
    "A Data Flow Diagram (DFD) illustrates how health reports, environmental",
    "inputs, risk analysis results, notifications, and reports move through the PULSE",
    "system. It clarifies the interaction among external entities, internal processes, and",
    "data stores that support surveillance operations and predictive alerting.",
]):
    d.text((130, 96 + i * 30), row, font=body, fill=INK)

bhw = (36, 400, 236, 96)
mid = (1528, 400, 236, 96)
adm = (36, 1090, 280, 96)
eng = (1470, 1090, 300, 116)
px, py, pw, ph = 500, 470, 800, 400
pr, pb = px + pw, py + ph
radius = 64

d.rounded_rectangle((px, py, pr, pb), radius=radius, outline=INK, width=2)
center("0", px + pw / 2, py + 52, proc_font)
for i, row in enumerate([
    "PULSE: Real-Time Syndromic",
    "Surveillance and Risk Forecasting using",
    "Isolation Forest Algorithms and",
    "Geospatial Data Fusion",
]):
    center(row, px + pw / 2, py + 128 + i * 30, proc_font)

entity(bhw, ["Barangay Health", "Worker(BHW)"], [box_font, box_font])
entity(mid, ["Midwife"], [box_font])
entity(adm, ["Admin"], [box_font])
entity(eng, ["Dual AI Engine", "Isolation Forest +", "Random Forest"], [box_font, sub_font, sub_font])

top_y = (276, 322, 368)
side_hi = (552, 604, 656)
side_lo = (700, 750, 800)
bot_y = (930, 990, 1050)

# Flat top of the process, split between the left and right sources.
left_drop = (920, 790, 660)
right_drop = (1040, 1140, 1220)
# Flat bottom, split the same way.
bot_left = (700, 840, 980)
bot_right = (1060, 1140, 1220)

# BHW -> process. Highest rail uses the leftmost stub.
for i, name in enumerate(["Location Data", "Syndromic Case Data", "Barangay Health Data"]):
    x0 = bhw[0] + (48, 118, 188)[i]
    y, xd = top_y[i], left_drop[i]
    stroke([(x0, bhw[1]), (x0, y), (xd, y), (xd, py - 14)])
    head(xd, py - 1, "down")
    label(name, x0 + 20, xd - 14, y)

# process -> BHW. Highest line is the shortest and lands nearest the process.
for i, name in enumerate(["View Dashboard Alerts", "View Risk Status", "Receive Notifications"]):
    x1 = bhw[0] + (188, 118, 48)[i]
    y = side_hi[i]
    stroke([(px, y), (x1, y), (x1, bhw[1] + bhw[3] + 14)])
    head(x1, bhw[1] + bhw[3] + 1, "up")
    label(name, x1 + 12, px - 12, y)

# Midwife -> process. Highest rail uses the rightmost stub.
for i, name in enumerate(["Personal Information", "Case Report Data"]):
    x0 = mid[0] + (188, 70)[i]
    y, xd = top_y[i], right_drop[i]
    stroke([(x0, mid[1]), (x0, y), (xd, y), (xd, py - 14)])
    head(xd, py - 1, "down")
    label(name, xd + 14, x0 - 14, y)

# process -> Midwife. Highest line lands nearest the process.
for i, name in enumerate(["View Data", "View Alerts / Notifications", "Manage Information"]):
    x1 = mid[0] + (48, 118, 188)[i]
    y = side_hi[i]
    stroke([(pr, y), (x1, y), (x1, mid[1] + mid[3] + 14)])
    head(x1, mid[1] + mid[3] + 1, "up")
    label(name, pr + 12, x1 - 12, y)

# process -> Admin. Highest line reaches farthest left.
for i, name in enumerate(["System logs", "Alert Data / Monitoring", "Report / Risk Maps"]):
    x1 = adm[0] + (42, 96, 150)[i]
    y = side_lo[i]
    stroke([(px, y), (x1, y), (x1, adm[1] - 14)])
    head(x1, adm[1] - 1, "down")
    label(name, x1 + 14, px - 12, y)

# Admin -> process. Stubs stay to the right of the downward arrows.
for i, name in enumerate(["User Management", "Case Record Updates", "Data Module Configuration"]):
    x0 = adm[0] + (174, 214, 258)[i]
    y, xd = bot_y[i], bot_left[i]
    stroke([(x0, adm[1]), (x0, y), (xd, y), (xd, pb + 14)])
    head(xd, pb + 1, "up")
    label(name, min(x0, xd) + 12, max(x0, xd) - 12, y)

# process -> Dual AI Engine. Highest line reaches farthest right.
for i, name in enumerate(["Historical Incident Data", "Anomaly Results", "Geo-Spatial Map"]):
    x1 = eng[0] + (275, 230, 185)[i]
    y = side_lo[i]
    stroke([(pr, y), (x1, y), (x1, eng[1] - 14)])
    head(x1, eng[1] - 1, "down")
    label(name, pr + 12, x1 - 12, y)

# Dual AI Engine -> process. Stubs stay to the right of those downward arrows.
for i, name in enumerate(["Alert Acknowledgement", "Investigation Update", "Response Logs"]):
    # Up-stubs stay left of the downward arrows. The top rail is the longest.
    x0 = eng[0] + (140, 85, 30)[i]
    y, xd = bot_y[i], bot_right[i]
    stroke([(x0, eng[1]), (x0, y), (xd, y), (xd, pb + 14)])
    head(xd, pb + 1, "up")
    label(name, min(x0, xd) + 10, max(x0, xd) - 10, y)

path = r"c:\DJANGO\djangotutorial\docs\data-flow-diagram.png"
img.save(path, "PNG")
print(path)
