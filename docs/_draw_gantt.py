"""Draw the PULSE capstone Gantt chart from PULSE_GANTT_CHART.txt."""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SOURCE = Path(r"c:\DJANGO\PULSE_GANTT_CHART.txt")
text = SOURCE.read_text(encoding="utf-8")

phases = []
current = None
phase_re = re.compile(r"^PHASE\s+(\d+)\s+[—-]\s+(.+?)\s+\(Weeks\s+(.+)\)\s*$")

for raw in text.splitlines():
    line = raw.strip()
    phase_match = phase_re.match(line)
    if phase_match:
        current = {
            "id": int(phase_match.group(1)),
            "name": phase_match.group(2).strip(),
            "weeks": phase_match.group(3).strip(),
            "tasks": [],
        }
        phases.append(current)
        continue
    if current is None or not line[:1].isdigit() or "|" not in line:
        continue
    parts = [part.strip() for part in line.split("|")]
    if len(parts) < 8 or not parts[0].isdigit():
        continue
    current["tasks"].append({
        "id": int(parts[0]),
        "name": parts[2],
        "start": int(parts[4]),
        "end": int(parts[5]),
        "status": parts[7],
    })

WEEKS = max(task["end"] for phase in phases for task in phase["tasks"])
LABEL_W = 470
WEEK_W = 34
LEFT = 36
TOP = 118
ROW_H = 22
PHASE_H = 28
RIGHT_PAD = 28
BOTTOM_PAD = 56

rows = 0
for phase in phases:
    rows += 1 + len(phase["tasks"])

width = LEFT + LABEL_W + WEEKS * WEEK_W + RIGHT_PAD
height = TOP + rows * ROW_H + (len(phases) * (PHASE_H - ROW_H)) + BOTTOM_PAD

img = Image.new("RGB", (width, height), "white")
d = ImageDraw.Draw(img)
INK = (23, 23, 23)
MUTED = (100, 116, 139)
GRID = (226, 232, 240)
PHASE_BG = (241, 245, 249)
DONE = (30, 64, 110)
PARTIAL = (180, 83, 9)
PLANNED = (148, 163, 184)

title_font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 28)
sub_font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 15)
phase_font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 13)
task_font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 12)
week_font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 11)
legend_font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 13)


def text_width(value, font):
    box = d.textbbox((0, 0), value, font=font)
    return box[2] - box[0]


d.text((LEFT, 24), "PULSE Gantt Chart", font=title_font, fill=INK)
d.text(
    (LEFT, 62),
    f"Public Health Unified Surveillance and Epidemiology  ·  Weeks 1–{WEEKS}",
    font=sub_font,
    fill=MUTED,
)

legend = [("Done", DONE, True), ("Partial", PARTIAL, True), ("Planned", PLANNED, False)]
legend_x = width - 360
for label, color, filled in legend:
    d.rounded_rectangle((legend_x, 66, legend_x + 28, 80), radius=3, outline=color, width=2, fill=color if filled else "white")
    d.text((legend_x + 36, 64), label, font=legend_font, fill=INK)
    legend_x += 110

chart_top = TOP
chart_bottom = height - BOTTOM_PAD + 8
grid_left = LEFT + LABEL_W

for week in range(1, WEEKS + 1):
    x = grid_left + (week - 1) * WEEK_W
    d.line((x, chart_top - 22, x, chart_bottom), fill=GRID, width=1)
    label = str(week)
    d.text((x + (WEEK_W - text_width(label, week_font)) / 2, chart_top - 20), label, font=week_font, fill=MUTED)
d.line((grid_left + WEEKS * WEEK_W, chart_top - 22, grid_left + WEEKS * WEEK_W, chart_bottom), fill=GRID, width=1)
week_label = "Week"
d.text((grid_left - text_width(week_label, week_font) - 10, chart_top - 20), week_label, font=week_font, fill=MUTED)

y = chart_top
for phase in phases:
    d.rectangle((LEFT, y, width - RIGHT_PAD, y + PHASE_H), fill=PHASE_BG)
    d.text(
        (LEFT + 8, y + 6),
        f"Phase {phase['id']}  ·  {phase['name']}   (Weeks {phase['weeks']})",
        font=phase_font,
        fill=INK,
    )
    y += PHASE_H
    for task in phase["tasks"]:
        name = f"{task['id']:>2}   {task['name']}"
        d.text((LEFT + 8, y + 4), name, font=task_font, fill=INK)
        x0 = grid_left + (task["start"] - 1) * WEEK_W + 3
        x1 = grid_left + task["end"] * WEEK_W - 3
        bar = (x0, y + 4, x1, y + ROW_H - 4)
        if task["status"] == "DONE":
            d.rounded_rectangle(bar, radius=3, fill=DONE)
        elif task["status"] == "PARTIAL":
            d.rounded_rectangle(bar, radius=3, fill=PARTIAL)
        else:
            d.rounded_rectangle(bar, radius=3, outline=PLANNED, width=2, fill="white")
        y += ROW_H

d.line((grid_left, chart_top, width - RIGHT_PAD, chart_top), fill=GRID, width=1)
d.rectangle((LEFT, chart_top, width - RIGHT_PAD, y), outline=(203, 213, 225), width=1)

out = Path(r"c:\DJANGO\djangotutorial\docs\gantt-chart.png")
img.save(out, "PNG")
print(f"{out}  {width}x{height}  tasks={sum(len(p['tasks']) for p in phases)} phases={len(phases)}")
