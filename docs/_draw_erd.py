"""Chen-style ERD of the live PULSE database."""
from PIL import Image, ImageDraw, ImageFont

W, H = 2200, 1680
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
INK = (17, 17, 17)

title_font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 32)
entity_font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 18)
attr_font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 13)


def text_size(text, font):
    box = d.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def entity_box(cx, cy, label, width=200, height=58):
    x0, y0 = cx - width / 2, cy - height / 2
    d.rectangle((x0, y0, x0 + width, y0 + height), outline=INK, width=2, fill="white")
    tw, th = text_size(label, entity_font)
    d.text((cx - tw / 2, cy - th / 2 - 1), label, font=entity_font, fill=INK)
    return (x0, y0, width, height)


def draw_attributes(box, labels):
    """Two or three rows of ovals above the entity, spokes to the top edge."""
    items = []
    for label in labels:
        tw, th = text_size(label, attr_font)
        items.append((label, tw + 22, th + 14))
    rows, row, row_w = [], [], 0
    max_w = 360
    for item in items:
        if row and row_w + item[1] + 10 > max_w:
            rows.append(row)
            row, row_w = [], 0
        row.append(item)
        row_w += item[1] + 10
    if row:
        rows.append(row)

    cx = box[0] + box[2] / 2
    top_y = box[1] - 8
    placed = []
    for row in reversed(rows):
        width = sum(item[1] for item in row) + 10 * (len(row) - 1)
        row_h = max(item[2] for item in row)
        top_y -= row_h
        x = cx - width / 2
        for label, ow, oh in row:
            placed.append((label, x, top_y, ow, oh))
            x += ow + 10
        top_y -= 12

    attach_x = cx
    attach_y = box[1]
    for label, x, y, ow, oh in placed:
        d.line((x + ow / 2, y + oh, attach_x, attach_y), fill=INK, width=1)
    for label, x, y, ow, oh in placed:
        d.ellipse((x, y, x + ow, y + oh), outline=INK, width=2, fill="white")
        tw, th = text_size(label, attr_font)
        d.text((x + (ow - tw) / 2, y + (oh - th) / 2 - 1), label, font=attr_font, fill=INK)


def stroke(points):
    d.line(points, fill=INK, width=2)


d.text((48, 28), "Entity Relationship Diagram", font=title_font, fill=INK)

# Column centers and row centers. Ovals sit above each box.
# Row 1
admins = entity_box(250, 420, "Admins")
users = entity_box(780, 420, "Users")
sessions = entity_box(1320, 420, "Surveillance Sessions", 250)
symptoms = entity_box(1880, 420, "Symptoms")

# Row 2
barangays = entity_box(250, 920, "Barangays")
patients = entity_box(780, 920, "Patients")
reports = entity_box(1320, 920, "Surveillance Reports", 250)
cases = entity_box(1880, 920, "Patient Cases", 210)

# Row 3
environment = entity_box(250, 1460, "Environmental Data", 230)
assessments = entity_box(780, 1460, "Risk Assessments", 220)
risk_logs = entity_box(1320, 1460, "Barangay Risk Logs", 240)
notifications = entity_box(1880, 1460, "App Notifications", 230)

draw_attributes(admins, [
    "admin_id (PK)", "first_name", "last_name", "email", "assigned_office", "status",
])
draw_attributes(users, [
    "user_id (PK)", "first_name", "last_name", "email", "role", "barangay_text", "status",
])
draw_attributes(sessions, [
    "session_id (PK)", "submitted_by (FK)", "syndrome_type", "patient_count", "session_date",
])
draw_attributes(symptoms, [
    "symptom_id (PK)", "code", "name", "syndromic_group",
])
draw_attributes(barangays, [
    "barangay_id (PK)", "barangay_name", "city", "population", "coordinates",
])
draw_attributes(patients, [
    "patient_id (PK)", "full_name", "sex", "birthdate", "address", "barangay_id (FK)",
])
draw_attributes(reports, [
    "report_id (PK)", "patient_id (FK)", "barangay_id (FK)", "submitted_by (FK)",
    "validated_by (FK)", "syndrome_type", "suspected_disease", "status",
])
draw_attributes(cases, [
    "case_id (PK)", "report_id (FK)", "session_id (FK)", "barangay_id (FK)",
    "age", "sex", "date_of_onset",
])
draw_attributes(environment, [
    "env_id (PK)", "barangay_id (FK)", "temperature", "humidity", "rainfall", "recorded_at",
])
draw_attributes(assessments, [
    "assessment_id (PK)", "report_id (FK)", "barangay_id (FK)",
    "anomaly_score", "risk_score", "risk_level",
])
draw_attributes(risk_logs, [
    "risk_log_id (PK)", "barangay", "syndrome", "anomaly_score",
    "final_risk_score", "risk_level", "is_active_alert",
])
draw_attributes(notifications, [
    "notification_id (PK)", "source_report_id (FK)", "disease", "barangay_name",
    "severity_level", "review_status", "recommendation_text",
])

def right(box):
    return box[0] + box[2]


def bottom(box):
    return box[1] + box[3]


def mid_y(box):
    return box[1] + box[3] / 2


# Same-row links, along the open side of each box.
stroke([(right(users), mid_y(users)), (sessions[0], mid_y(sessions))])
stroke([(right(barangays), mid_y(barangays)), (patients[0], mid_y(patients))])
stroke([(right(patients), mid_y(patients) + 16), (reports[0], mid_y(reports) + 16)])
stroke([(right(reports), mid_y(reports) + 16), (cases[0], mid_y(cases) + 16)])

# Admins validate a report. Users submit a report.
stroke([(admins[0] + 40, bottom(admins)), (admins[0] + 40, 500),
        (1060, 500), (1060, mid_y(reports) - 16), (reports[0], mid_y(reports) - 16)])
stroke([(users[0] + users[2] / 2, bottom(users)), (users[0] + users[2] / 2, 570),
        (1000, 570), (1000, mid_y(reports)), (reports[0], mid_y(reports))])

# A session groups the report and the patient cases.
stroke([(right(sessions) - 36, bottom(sessions)), (right(sessions) - 36, 640),
        (1560, 640), (1560, mid_y(reports) - 16), (right(reports), mid_y(reports) - 16)])
stroke([(right(sessions) - 12, bottom(sessions)), (right(sessions) - 12, 730),
        (2140, 730), (2140, mid_y(cases)), (right(cases), mid_y(cases))])

# Symptoms recorded on a patient case.
stroke([(symptoms[0] + 24, bottom(symptoms)), (symptoms[0] + 24, 690),
        (1640, 690), (1640, mid_y(cases) - 16), (cases[0], mid_y(cases) - 16)])

# Lines under the middle row stay on separate lanes so they do not cross.
stroke([(right(reports) - 30, bottom(reports)), (right(reports) - 30, 990),
        (2140, 990), (2140, mid_y(notifications)), (right(notifications), mid_y(notifications))])
stroke([(barangays[0] + 36, bottom(barangays)), (barangays[0] + 36, 1040),
        (reports[0] + 48, 1040), (reports[0] + 48, bottom(reports))])
stroke([(reports[0] + 100, bottom(reports)), (reports[0] + 100, 1100),
        (1040, 1100), (1040, mid_y(assessments)), (right(assessments), mid_y(assessments))])
stroke([(barangays[0] + 78, bottom(barangays)), (barangays[0] + 78, 1160),
        (cases[0] + 40, 1160), (cases[0] + 40, bottom(cases))])
stroke([(barangays[0] + 120, bottom(barangays)), (barangays[0] + 120, 1230),
        (560, 1230), (560, mid_y(assessments)), (assessments[0], mid_y(assessments))])
stroke([(barangays[0], mid_y(barangays) - 14), (48, mid_y(barangays) - 14),
        (48, 1600), (risk_logs[0] + risk_logs[2] / 2, 1600),
        (risk_logs[0] + risk_logs[2] / 2, bottom(risk_logs))])
stroke([(barangays[0], mid_y(barangays) + 14), (72, mid_y(barangays) + 14),
        (72, mid_y(environment)), (environment[0], mid_y(environment))])

path = r"c:\DJANGO\djangotutorial\docs\entity-relationship-diagram.png"
img.save(path, "PNG")
print(path)
