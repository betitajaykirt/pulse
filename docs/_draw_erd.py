"""Current PULSE database, drawn in the original Chen format.

Rectangles are tables. Ovals on the arc above a rectangle are its columns.
A line between rectangles is a foreign key. Django framework tables are omitted.
"""
import math

from PIL import Image, ImageDraw, ImageFont

W, H = 5400, 4300
img = Image.new('RGB', (W, H), 'white')
d = ImageDraw.Draw(img)
INK = (17, 17, 17)
OVALS = []
BOXES = []
LINES = []

entity_font = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 17)
attr_font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 13)

# Positions follow the reference figure:
# staff at the upper left, the case across the top and middle,
# alerts on the right, and barangay / weather / prediction along the bottom.


def text_size(text, font):
    box = d.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def entity_box(cx, cy, label, width=210, height=48):
    return [cx - width / 2, cy - height / 2, width, height, label]


def paint_box(box):
    BOXES.append(box)
    d.rectangle(
        (box[0], box[1], box[0] + box[2], box[1] + box[3]),
        outline=INK, width=2, fill='white',
    )
    tw, th = text_size(box[4], entity_font)
    d.text(
        (box[0] + (box[2] - tw) / 2, box[1] + (box[3] - th) / 2 - 1),
        box[4], font=entity_font, fill=INK,
    )


def right(box):
    return box[0] + box[2]


def bottom(box):
    return box[1] + box[3]


def mid_x(box):
    return box[0] + box[2] / 2


def mid_y(box):
    return box[1] + box[3] / 2


def stroke(points):
    LINES.append(list(points))
    d.line(points, fill=INK, width=2)


def hlink(a, b, dy=0):
    y = mid_y(a) + dy
    stroke([(right(a), y), (b[0], mid_y(b) + dy)])


def down_to_side(src, dst, lane, gap, enter='left', src_dx=0, end_dy=0):
    """Leave the bottom of src, travel in the open gap, enter a side of dst."""
    start_x = mid_x(src) + src_dx
    end_x = dst[0] if enter == 'left' else right(dst)
    end_y = mid_y(dst) + end_dy
    stroke([
        (start_x, bottom(src)),
        (start_x, lane),
        (gap, lane),
        (gap, end_y),
        (end_x, end_y),
    ])


def layout_arc(box, labels, radius, lift):
    sized = []
    for label in labels:
        tw, th = text_size(label, attr_font)
        sized.append((label, tw + 18, max(th + 12, 26)))
    n = len(sized)
    placed = []
    for _ in range(24):
        placed = []
        crowded = False
        centers = []
        for i, (label, ow, oh) in enumerate(sized):
            t = 0.5 if n == 1 else i / (n - 1)
            theta = math.radians(-60 + 120 * t)
            cx = mid_x(box) + math.sin(theta) * radius
            cy = box[1] - lift - 16 - math.cos(theta) * (radius * 0.34)
            rect = [cx - ow / 2, cy - oh / 2, ow, oh]
            for (pcx, pcy, pow_, poh) in centers:
                needed = (ow + pow_) / 2 + 12
                if math.hypot(cx - pcx, cy - pcy) < needed:
                    crowded = True
            centers.append((cx, cy, ow, oh))
            placed.append((label, rect))
        if not crowded:
            return placed
        radius += 18
    return placed


def arcs_crowd(a, b):
    for _label, rect in a:
        cx = rect[0] + rect[2] / 2
        cy = rect[1] + rect[3] / 2
        for _other, orect in b:
            ocx = orect[0] + orect[2] / 2
            ocy = orect[1] + orect[3] / 2
            needed = (rect[2] + orect[2]) / 2 + 14
            if math.hypot(cx - ocx, cy - ocy) < needed:
                return True
    return False


def fan_attributes(box, labels):
    if len(labels) > 5:
        split = (len(labels) + 1) // 2
        outer_r = 300
        placed = []
        for _ in range(16):
            outer = layout_arc(box, labels[:split], outer_r, 110)
            inner = layout_arc(box, labels[split:], 150, 0)
            placed = outer + inner
            if not arcs_crowd(outer, inner):
                break
            outer_r += 28
    else:
        placed = layout_arc(box, labels, 120, 0)
    anchor = (mid_x(box), box[1])
    for _label, rect in placed:
        stroke([(rect[0] + rect[2] / 2, rect[1] + rect[3] / 2), anchor])
    for label, rect in placed:
        OVALS.append((label, rect, box[4]))
        d.ellipse(
            (rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3]),
            outline=INK, width=2, fill='white',
        )
        tw, th = text_size(label, attr_font)
        d.text(
            (rect[0] + (rect[2] - tw) / 2, rect[1] + (rect[3] - th) / 2 - 1),
            label, font=attr_font, fill=INK,
        )


# The twelve core tables use the same positions as the example figure.
# Measured from that image, as a fraction of its width and height.
def placed(fx, fy, label, width):
    return entity_box(180 + fx * 4400, 50 + fy * 3200, label, width)


users = placed(0.206, 0.166, 'Users', 150)
reports = placed(0.472, 0.205, 'Surveillance Reports', 250)
sessions = placed(0.331, 0.338, 'Surveillance Sessions', 250)
alerts = placed(0.638, 0.348, 'Alerts', 150)
app_notifs = placed(0.794, 0.323, 'App Notifications', 220)
patients = placed(0.415, 0.594, 'Patients', 170)
cases = placed(0.626, 0.622, 'Patient Cases', 190)
admins = placed(0.109, 0.618, 'Admins', 160)
risk = placed(0.896, 0.608, 'Risk Analysis', 180)
barangays = placed(0.338, 0.838, 'Barangays', 180)
environment = placed(0.562, 0.838, 'Environmental Data', 230)
predictions = placed(0.772, 0.832, 'ML/AI Predictions', 220)

# The other tables stay in the open margins around that arrangement.
super_admins = entity_box(380, mid_y(users), 'Super Admins', 190)
field_tasks = entity_box(380, mid_y(sessions), 'Field Tasks', 180)
login_attempts = entity_box(380, 1580, 'Login Attempts', 200)
notif_logs = entity_box(3300, 1620, 'Notification Logs', 210)
notif_reads = entity_box(4450, 1420, 'Notification Reads', 210)
assessments = entity_box(900, 2300, 'Risk Assessments', 210)
threshold_logs = entity_box(1450, 2300, 'Threshold Logs', 190)
case_symptoms = entity_box(3450, 2300, 'Case Symptoms', 200)
symptoms = entity_box(3850, 2300, 'Symptoms', 160)
epidemic = entity_box(860, mid_y(barangays), 'Epidemic Status', 200)
risk_logs = entity_box(4700, mid_y(predictions), 'Barangay Risk Logs', 220)

# Long spines, like the example: a center drop, a bottom rail,
# and the alert chain down the right side.
RAIL = 2420
CENTER = mid_x(reports)

stroke([(right(field_tasks), mid_y(field_tasks)), (820, mid_y(field_tasks)), (820, mid_y(users)), (users[0], mid_y(users))])
stroke([(mid_x(field_tasks), bottom(field_tasks)), (mid_x(field_tasks), 1320), (1280, 1320), (1280, 820), (CENTER - 70, 820), (CENTER - 70, bottom(reports))])
stroke([(sessions[0], mid_y(sessions)), (1280, mid_y(sessions)), (1280, 820)])
stroke([(mid_x(users), bottom(users)), (mid_x(users), 820), (CENTER - 30, 820), (CENTER - 30, bottom(reports))])
stroke([(CENTER + 110, bottom(reports)), (CENTER + 110, RAIL)])
stroke([(right(patients), mid_y(patients)), (CENTER + 110, mid_y(patients)), (CENTER + 110, RAIL)])
stroke([(mid_x(patients), bottom(patients)), (mid_x(patients), RAIL)])
stroke([(mid_x(cases), bottom(cases)), (mid_x(cases), RAIL)])
stroke([(right(sessions), bottom(sessions)), (1900, bottom(sessions)), (1900, 1340), (2480, 1340), (2480, mid_y(cases)), (cases[0], mid_y(cases))])
stroke([(right(cases), mid_y(cases) + 12), (3220, mid_y(cases) + 12), (3220, mid_y(case_symptoms)), (case_symptoms[0], mid_y(case_symptoms))])
stroke([(right(case_symptoms), mid_y(case_symptoms) - 12), (symptoms[0], mid_y(symptoms))])
stroke([(CENTER + 110, RAIL), (1280, RAIL), (1280, mid_y(barangays)), (barangays[0], mid_y(barangays))])
stroke([(CENTER + 110, RAIL), (2480, RAIL), (2480, mid_y(environment)), (environment[0], mid_y(environment))])
stroke([(right(barangays), mid_y(barangays)), (environment[0], mid_y(environment))])
stroke([(right(alerts), mid_y(alerts)), (3700, mid_y(alerts)), (3700, mid_y(risk)), (risk[0], mid_y(risk))])
stroke([(mid_x(risk) + 40, bottom(risk)), (mid_x(risk) + 40, 2380), (4000, 2380), (4000, mid_y(predictions)), (right(predictions), mid_y(predictions))])
stroke([(right(alerts), bottom(alerts) - 6), (3600, bottom(alerts) - 6), (3600, mid_y(notif_logs)), (right(notif_logs), mid_y(notif_logs))])
stroke([(mid_x(app_notifs) + 80, bottom(app_notifs)), (mid_x(app_notifs) + 80, 1640), (mid_x(notif_reads), 1640), (mid_x(notif_reads), bottom(notif_reads))])
stroke([(right(reports), bottom(reports) - 8), (3380, bottom(reports) - 8), (3380, mid_y(app_notifs)), (app_notifs[0], mid_y(app_notifs))])
stroke([(right(epidemic), mid_y(epidemic)), (barangays[0], mid_y(barangays) + 10)])
stroke([(threshold_logs[0], mid_y(threshold_logs)), (1180, mid_y(threshold_logs)), (1180, RAIL)])
stroke([(mid_x(threshold_logs), bottom(threshold_logs)), (mid_x(threshold_logs), RAIL)])
stroke([(right(assessments), mid_y(assessments)), (1180, mid_y(assessments))])
stroke([(mid_x(assessments), bottom(assessments)), (mid_x(assessments), RAIL)])

RELATION_LINES = [list(line) for line in LINES]

boxes = [
    super_admins, admins, users, field_tasks, sessions, login_attempts,
    barangays, patients, reports, cases, case_symptoms, symptoms,
    environment, epidemic, assessments, threshold_logs, app_notifs, notif_reads,
    predictions, risk, alerts, notif_logs, risk_logs,
]
for box in boxes:
    paint_box(box)

fan_attributes(super_admins, ['id (PK)', 'username', 'email', 'password_hash', 'status'])
fan_attributes(admins, ['id (PK)', 'username', 'email', 'assigned_office', 'password_hash', 'status'])
fan_attributes(users, ['id (PK)', 'username', 'email', 'role', 'barangay_text', 'password_hash', 'status'])
fan_attributes(field_tasks, ['id (PK)', 'assigned_to_id (FK)', 'assigned_by_id (FK)', 'report_id (FK)', 'title', 'status'])
fan_attributes(sessions, ['id (PK)', 'submitted_by (FK)', 'syndrome_type', 'patient_count', 'session_date'])
fan_attributes(login_attempts, ['id (PK)', 'email', 'success', 'ip_address', 'attempted_at'])
fan_attributes(barangays, ['barangay_id (PK)', 'barangay_name', 'city', 'population', 'coordinates'])
fan_attributes(patients, ['patient_id (PK)', 'full_name', 'sex', 'birthdate', 'address', 'barangay_id (FK)'])
fan_attributes(reports, [
    'id (PK)', 'patient_id (FK)', 'barangay_id (FK)', 'submitted_by (FK)',
    'validated_by (FK)', 'session_id (FK)', 'syndrome_type', 'status',
])
fan_attributes(cases, ['id (PK)', 'session_id (FK)', 'report_id (FK)', 'barangay_id (FK)', 'patient_name', 'age', 'sex'])
fan_attributes(case_symptoms, ['id (PK)', 'patientcase_id (FK)', 'symptom_id (FK)'])
fan_attributes(symptoms, ['id (PK)', 'code', 'name', 'syndromic_group'])
fan_attributes(environment, ['id (PK)', 'barangay_id (FK)', 'temperature', 'humidity', 'rainfall', 'recorded_at'])
fan_attributes(epidemic, ['id (PK)', 'barangay_id (FK)', 'disease_label', 'threshold_status', 'confirmed_count'])
fan_attributes(assessments, ['id (PK)', 'report_id (FK)', 'barangay_id (FK)', 'anomaly_score', 'risk_score', 'risk_level'])
fan_attributes(threshold_logs, ['id (PK)', 'barangay_id (FK)', 'report_id (FK)', 'disease_label', 'threshold_status'])
fan_attributes(app_notifs, ['id (PK)', 'source_report_id (FK)', 'disease', 'barangay_name', 'severity_level', 'review_status'])
fan_attributes(notif_reads, ['id (PK)', 'notification_id (FK)', 'user_id', 'user_type', 'read_at'])
fan_attributes(predictions, ['prediction_id (PK)', 'disease_type', 'risk_score', 'prediction_probability', 'algorithm_used'])
fan_attributes(risk, ['analysis_id (PK)', 'prediction_id (FK)', 'risk_score', 'anomaly_flag', 'analysis_date'])
fan_attributes(alerts, ['alert_id (PK)', 'analysis_id (FK)', 'alert_level', 'alert_type', 'status'])
fan_attributes(notif_logs, ['id (PK)', 'alert_id (FK)', 'recipient_role', 'channel', 'delivery_status'])
fan_attributes(risk_logs, ['id (PK)', 'barangay', 'syndrome', 'anomaly_score', 'final_risk_score', 'risk_level'])

# These tables are in the database and have no foreign key.
ref_rows = [
    ('Sessions', 170, ['id (PK)', 'user_id', 'user_type', 'expires_at', 'invalidated']),
    ('Disease Thresholds', 220, ['id (PK)', 'category_level', 'warning_threshold', 'outbreak_threshold']),
    ('Outbreak Thresholds', 230, ['id (PK)', 'disease_label', 'case_threshold', 'rolling_window_days']),
    ('Added Diseases', 200, ['id (PK)', 'name', 'category', 'symptom_codes', 'is_active']),
    ('Mitigation Protocols', 220, ['id (PK)', 'disease_label', 'action_text', 'priority']),
    ('Recommendation Revisions', 260, ['id (PK)', 'scope_disease', 'status', 'created_by_id']),
    ('Audit Logs', 170, ['id (PK)', 'actor_id', 'actor_type', 'action']),
    ('System Logs', 170, ['id (PK)', 'user_id', 'activity_type', 'module']),
]
ref_x = [700, 1900, 3100, 4400]
for i, (label, width, attrs) in enumerate(ref_rows):
    box = entity_box(ref_x[i % 4], 3600 if i < 4 else 4000, label, width)
    paint_box(box)
    fan_attributes(box, attrs)


def rect_of(box):
    return box[0], box[1], box[0] + box[2], box[1] + box[3]


def point_in_rect(px, py, rect, pad):
    return rect[0] + pad < px < rect[2] - pad and rect[1] + pad < py < rect[3] - pad


def segments_cross(a, b, c, d):
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    d1 = cross(c, d, a)
    d2 = cross(c, d, b)
    d3 = cross(a, b, c)
    d4 = cross(a, b, d)
    if d1 * d2 < 0 and d3 * d4 < 0:
        return True
    return False


def segment_hits_rect(p, q, rect):
    if point_in_rect(p[0], p[1], rect, 3) or point_in_rect(q[0], q[1], rect, 3):
        return True
    edges = [
        ((rect[0], rect[1]), (rect[2], rect[1])),
        ((rect[2], rect[1]), (rect[2], rect[3])),
        ((rect[2], rect[3]), (rect[0], rect[3])),
        ((rect[0], rect[3]), (rect[0], rect[1])),
    ]
    return any(segments_cross(p, q, e0, e1) for e0, e1 in edges)


problems = []
for box in BOXES:
    rect = rect_of(box)
    if rect[0] < 8 or rect[1] < 8 or rect[2] > W - 8 or rect[3] > H - 8:
        problems.append('box off canvas: ' + box[4])
    for other in BOXES:
        if other is box:
            continue
        orect = rect_of(other)
        if rect[0] < orect[2] and orect[0] < rect[2] and rect[1] < orect[3] and orect[1] < rect[3]:
            pair = tuple(sorted((box[4], other[4])))
            message = 'boxes overlap: %s / %s' % pair
            if message not in problems:
                problems.append(message)
    for line in LINES:
        for p, q in zip(line, line[1:]):
            if segment_hits_rect(p, q, rect):
                problems.append('line through %s via %s -> %s' % (box[4], p, q))
                break

for i, (label, rect, owner) in enumerate(OVALS):
    left, top, width, height = rect
    if left < 4 or top < 4 or left + width > W - 4 or top + height > H - 4:
        problems.append('oval off canvas: %s on %s' % (label, owner))
    cx = left + width / 2
    cy = top + height / 2
    oval_rect = (left, top, left + width, top + height)
    for line in RELATION_LINES:
        for p, q in zip(line, line[1:]):
            if segment_hits_rect(p, q, oval_rect):
                problems.append('line through oval %s on %s via %s -> %s' % (label, owner, p, q))
                break
    for olabel, orect, oowner in OVALS[i + 1:]:
        ocx = orect[0] + orect[2] / 2
        ocy = orect[1] + orect[3] / 2
        needed = (width + orect[2]) / 2 + 8
        if math.hypot(cx - ocx, cy - ocy) < needed:
            problems.append('ovals overlap: %s (%s) / %s (%s)' % (label, owner, olabel, oowner))

print('collisions', len(problems))
for item in problems[:60]:
    print(item)

path = r'c:\DJANGO\djangotutorial\docs\entity-relationship-diagram.png'
img.save(path, 'PNG')
print(path)
