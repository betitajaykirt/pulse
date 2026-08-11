"""
PULSE Django ORM models — mapped to existing pulse_db tables.
Legacy tables (barangays, alerts) and PulseCapstone tables coexist in pulse_db.
"""
from decimal import Decimal, InvalidOperation
from django.db import models


# ── Super Admins (table: super_admins) ───────────────────────────

class SuperAdmin(models.Model):
    username = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    suffix = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True)
    contact_number = models.CharField(max_length=20, null=True, blank=True)
    password_hash = models.CharField(max_length=255)
    profile_image = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=10, default='active')
    remember_token = models.CharField(max_length=255, null=True, blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'super_admins'
        managed = False

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# ── Admins (table: admins — no superadmin_id column in pulse_db) ──

class Admin(models.Model):
    username = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    suffix = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True)
    contact_number = models.CharField(max_length=20, null=True, blank=True)
    assigned_office = models.CharField(max_length=150, null=True, blank=True)
    password_hash = models.CharField(max_length=255)
    profile_image = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=10, default='active')
    remember_token = models.CharField(max_length=255, null=True, blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'admins'
        managed = False

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# ── Users (table: users) ──────────────────────────────────────────

class User(models.Model):
    ROLE_CHOICES = [
        ('encoder', 'Encoder'),
        ('health_officer', 'Health Officer'),
        ('surveillance_officer', 'Surveillance Officer'),
        ('catchment_nurse', 'Catchment Nurse (OIC)'),
        ('barangay_health_worker', 'Barangay Health Worker'),
    ]

    username = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    suffix = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True)
    contact_number = models.CharField(max_length=20, null=True, blank=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=30)
    assigned_region = models.CharField(max_length=150, null=True, blank=True)
    designation = models.CharField(max_length=150, null=True, blank=True)
    assigned_cluster = models.CharField(max_length=150, null=True, blank=True)
    license_or_id_no = models.CharField(max_length=100, null=True, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    region_text = models.CharField(max_length=100, null=True, blank=True)
    province_text = models.CharField(max_length=100, null=True, blank=True)
    city_text = models.CharField(max_length=100, null=True, blank=True)
    barangay_text = models.CharField(max_length=100, null=True, blank=True)
    profile_image = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=10, default='active')
    first_login = models.BooleanField(default=True)
    remember_token = models.CharField(max_length=255, null=True, blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'users'
        managed = False

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"


# ── Barangays (legacy table: barangay_id PK, coordinates string) ─

class Barangay(models.Model):
    id = models.AutoField(primary_key=True, db_column='barangay_id')
    barangay_name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    coordinates = models.CharField(max_length=255)
    population = models.IntegerField()

    class Meta:
        db_table = 'barangays'
        managed = False

    def __str__(self):
        return self.barangay_name

    def _coord_parts(self):
        if not self.coordinates:
            return None, None
        parts = [p.strip() for p in str(self.coordinates).split(',')]
        if len(parts) >= 2:
            return parts[0], parts[1]
        return None, None

    @property
    def latitude(self):
        lat, _ = self._coord_parts()
        if lat is None:
            return None
        try:
            return Decimal(lat)
        except (InvalidOperation, ValueError):
            return None

    @property
    def longitude(self):
        _, lng = self._coord_parts()
        if lng is None:
            return None
        try:
            return Decimal(lng)
        except (InvalidOperation, ValueError):
            return None

    @property
    def risk_status(self):
        return 'low'

    @property
    def district(self):
        return None

    @property
    def last_reported_at(self):
        return None


# ── Patients (table: patients) ───────────────────────────────────

class Patient(models.Model):
    id = models.AutoField(primary_key=True, db_column='patient_id')
    full_name = models.CharField(max_length=255)
    sex = models.CharField(max_length=10)
    address = models.TextField()
    birthdate = models.DateField()
    barangay = models.ForeignKey(
        Barangay, on_delete=models.DO_NOTHING, db_column='barangay_id',
        related_name='patients',
    )

    class Meta:
        db_table = 'patients'
        managed = False

    def __str__(self):
        return self.full_name


# ── Surveillance Reports (table: surveillance_reports) ───────────

class SurveillanceReport(models.Model):
    CASE_STATUS_CHOICES = [
        ('Unclassified', 'Unclassified'),
        ('Pending ML Analysis', 'Pending ML Analysis'),
        ('Suspected', 'Suspected'),
        ('Probable', 'Probable'),
        ('Confirmed', 'Confirmed'),
        ('Closed', 'Closed'),
        ('Discarded', 'Discarded'),
    ]

    barangay = models.ForeignKey(
        Barangay, on_delete=models.DO_NOTHING, db_column='barangay_id',
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.SET_NULL,
        null=True, blank=True, db_column='patient_id',
        related_name='surveillance_reports',
    )
    submitted_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        null=True, blank=True, db_column='submitted_by',
        related_name='submitted_reports',
    )
    source_type = models.CharField(max_length=20, default='manual')
    syndrome_type = models.CharField(max_length=150)
    suspected_disease = models.CharField(max_length=150, null=True, blank=True)
    case_count = models.PositiveIntegerField(default=1)
    patient_name = models.CharField(max_length=255, default='Unknown Resident')
    civil_status = models.CharField(max_length=50, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    detailed_address = models.TextField(null=True, blank=True)
    is_student = models.BooleanField(default=False)
    grade_year_section = models.CharField(max_length=100, null=True, blank=True)
    school_name = models.CharField(max_length=255, null=True, blank=True)
    date_of_onset = models.DateField(null=True, blank=True)
    report_date = models.DateTimeField()
    case_classification = models.CharField(max_length=10, default='suspected')
    status = models.CharField(max_length=20, choices=CASE_STATUS_CHOICES, default='Suspected')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    validation_status = models.CharField(max_length=10, default='pending')
    resolution_outcome = models.CharField(max_length=50, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    is_anomaly = models.BooleanField(default=False)
    ml_anomaly_score = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True,
    )
    epidemic_threshold_status = models.CharField(max_length=32, default='')
    validated_by = models.ForeignKey(
        Admin, on_delete=models.DO_NOTHING,
        null=True, blank=True, db_column='validated_by',
        related_name='validated_reports',
    )
    remarks = models.TextField(null=True, blank=True)
    session = models.ForeignKey(
        'SurveillanceSession', on_delete=models.DO_NOTHING,
        null=True, blank=True, db_column='session_id',
        related_name='surveillance_reports',
    )

    @property
    def computed_risk_level(self):
        import re

        # 1. Direct label override from APTAS
        if hasattr(self, 'aptas_risk_level') and self.aptas_risk_level and self.aptas_risk_level.lower() != 'low':
            return self.aptas_risk_level

        score = None

        # 2. First priority: Use APTAS Final Composite Risk Score if present
        for attr in ['final_risk', 'final_score', 'aptas_score', 'risk_score']:
            val = getattr(self, attr, None)
            if val is not None:
                val = float(val)
                if 0.0 <= val <= 1.0:
                    score = val
                    break

        # 3. Second priority: If spatial/temporal/anomaly metrics exist, calculate dynamic composite weighted average
        if score is None:
            # Also check without '_score' suffix since API/JS payloads might omit it
            anom = getattr(self, 'anomaly_score', getattr(self, 'anomaly', None))
            temp = getattr(self, 'temporal_score', getattr(self, 'temporal', None))
            spat = getattr(self, 'spatial_score', getattr(self, 'spatial', None))
            
            if anom is not None and temp is not None and spat is not None:
                env = getattr(self, 'environmental_score', getattr(self, 'environmental', 0.5))
                if env is None: env = 0.5
                try:
                    score = (float(anom) * 0.3) + (float(temp) * 0.3) + (float(spat) * 0.2) + (float(env) * 0.2)
                except (ValueError, TypeError):
                    pass

        # 4. Third priority: Fallback to ML Diagnostic Confidence
        if score is None and self.remarks:
            match = re.search(r'ML Confidence:\s*([\d.]+)%', self.remarks, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1)) / 100.0
                except (ValueError, TypeError):
                    pass

        # 5. Last resort: use ml_anomaly_score only if it's positive (probability-like)
        if score is None and self.ml_anomaly_score is not None:
            val = float(self.ml_anomaly_score)
            if val > 0:
                score = val

        score = score or 0.0
        if score >= 0.85: return 'Critical'
        if score >= 0.65: return 'High'
        if score >= 0.45: return 'Moderate'
        return 'Low'
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'surveillance_reports'
        managed = False

    def __str__(self):
        return f"Report #{self.pk} — {self.syndrome_type}"


# ── Batch Entry: Surveillance Session (parent) ───────────────────

class SurveillanceSession(models.Model):
    submitted_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, db_column='submitted_by',
        related_name='surveillance_sessions',
    )
    case_classification = models.CharField(max_length=10, default='suspected')
    syndrome_type = models.CharField(max_length=150)
    source_type = models.CharField(max_length=20, default='BHW')
    patient_count = models.PositiveIntegerField(default=1)
    session_date = models.DateTimeField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'surveillance_sessions'
        managed = False

    def __str__(self):
        return f"Session #{self.pk} — {self.syndrome_type} ({self.patient_count} cases)"


# ── PIDSR syndromic symptom codes (ML feature set) ───────────────
from reports.pidsr_schema import (  # noqa: E402
    DISEASE_LABELS as PIDSR_DISEASE_LABELS,
    LEGACY_SYMPTOM_CODE_MAP,
    PIDSR_SYMPTOM_CODES,
    PIDSR_SYMPTOM_LABELS,
    SYMPTOM_CATEGORY_CODES,
    SYMPTOM_CATEGORY_GROUP_MAP,
    normalize_symptom_codes,
)

DEFAULT_SYNDROME_TYPE = 'Inconclusive Syndromic Pattern'
DEFAULT_INTAKE_STATUS = 'Unclassified'
DEFAULT_INTAKE_CLASSIFICATION = 'unassigned'

SYMPTOM_CATEGORY_CHOICES = [
    ('', 'All Symptoms'),
    ('systemic', 'Systemic'),
    ('pain', 'Pain'),
    ('gastrointestinal', 'Gastrointestinal (GI)'),
    ('dermatological', 'Skin / Vascular'),
    ('respiratory', 'Respiratory'),
    ('neurological', 'Neurological'),
    ('exposure', 'Exposure History (Group E)'),
]

SYNDROMIC_GROUP_CHOICES = [
    ('A', 'Group A — Systemic'),
    ('B', 'Group B — Pain'),
    ('C', 'Group C — Gastrointestinal (GI)'),
    ('D', 'Group D — Skin / Vascular'),
    ('R', 'Group R — Respiratory'),
    ('N', 'Group N — Neurological'),
    ('E', 'Group E — Exposure History'),
]


class Symptom(models.Model):
    """
    Admin-editable syndromic indicator.

    ``code`` is the stable ML/API key (maps to ``ml_pipeline.py`` feature columns).
    ``name`` is the alphabetically sorted label shown on the intake form.
    """

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    syndromic_group = models.CharField(max_length=1, choices=SYNDROMIC_GROUP_CHOICES)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'symptoms'
        managed = False
        ordering = ['name']

    def __str__(self):
        return self.name


# ── Disease mitigation protocols (map popup / CHO response playbook) ──

class MitigationProtocol(models.Model):
    """Actionable response steps keyed by ML / surveillance ``disease_label``."""

    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    CATEGORY_CHOICES = [
        ('environmental', 'Environmental'),
        ('logistical', 'Logistical'),
        ('medical', 'Medical'),
        ('public_warning', 'Public Warning'),
    ]

    disease_label = models.CharField(max_length=150, db_index=True)
    action_text = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    action_category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'mitigation_protocols'
        managed = False
        ordering = ['disease_label', '-priority', 'sort_order']
        constraints = [
            models.UniqueConstraint(
                fields=['disease_label', 'sort_order'],
                name='uniq_mitigation_disease_sort',
            ),
        ]

    def __str__(self):
        return f'{self.disease_label} — {self.action_text[:60]}'


# ── Dynamic PIDSR category thresholds (admin-editable) ───────────

class DiseaseCategoryThreshold(models.Model):
    """Epidemic thresholds per PIDSR surveillance category level."""

    category_level = models.CharField(max_length=32, unique=True)
    warning_threshold = models.PositiveSmallIntegerField(default=2)
    outbreak_threshold = models.PositiveSmallIntegerField(default=3)
    time_window_days = models.PositiveSmallIntegerField(default=7)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'disease_category_thresholds'
        managed = False
        ordering = ['category_level']

    def __str__(self):
        return (
            f'{self.category_level} — warn {self.warning_threshold}, '
            f'outbreak {self.outbreak_threshold} / {self.time_window_days}d'
        )


class OutbreakThreshold(models.Model):
    """Dynamic outbreak threshold configuration per disease."""

    disease_label = models.CharField(max_length=150, unique=True)
    case_threshold = models.PositiveSmallIntegerField(default=3)
    rolling_window_days = models.PositiveSmallIntegerField(default=7)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'outbreak_thresholds'
        managed = False
        ordering = ['disease_label']

    def __str__(self):
        return f'{self.disease_label} — threshold {self.case_threshold} / {self.rolling_window_days}d'


class BarangayEpidemicStatus(models.Model):
    """Latest threshold evaluation snapshot per barangay + disease (map indicators)."""

    barangay = models.ForeignKey(
        Barangay, on_delete=models.DO_NOTHING, db_column='barangay_id',
        related_name='epidemic_statuses',
    )
    disease_label = models.CharField(max_length=150)
    pidsr_category = models.CharField(max_length=32)
    threshold_status = models.CharField(max_length=32)
    confirmed_count = models.PositiveSmallIntegerField(default=0)
    evaluated_at = models.DateTimeField()

    class Meta:
        db_table = 'barangay_epidemic_statuses'
        managed = False
        constraints = [
            models.UniqueConstraint(
                fields=['barangay', 'disease_label'],
                name='uniq_barangay_disease_epidemic_status',
            ),
        ]

    def __str__(self):
        return f'{self.barangay_id} — {self.disease_label}: {self.threshold_status}'


class OutbreakThresholdLog(models.Model):
    """Audit trail when admin confirmation triggers threshold evaluation."""

    barangay = models.ForeignKey(
        Barangay, on_delete=models.DO_NOTHING, db_column='barangay_id',
    )
    report = models.ForeignKey(
        'SurveillanceReport', on_delete=models.DO_NOTHING,
        null=True, blank=True, db_column='report_id',
    )
    disease_label = models.CharField(max_length=150)
    pidsr_category = models.CharField(max_length=32)
    confirmed_count = models.PositiveSmallIntegerField(default=0)
    threshold_status = models.CharField(max_length=32)
    warning_threshold = models.PositiveSmallIntegerField(null=True, blank=True)
    outbreak_threshold = models.PositiveSmallIntegerField(null=True, blank=True)
    time_window_days = models.PositiveSmallIntegerField(default=7)
    actor_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'outbreak_threshold_logs'
        managed = False
        ordering = ['-created_at']

    def __str__(self):
        return f'Log #{self.pk} — {self.threshold_status}'


# ── Batch Entry: Patient Case (child) ────────────────────────────

class PatientCase(models.Model):
    SEX_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]

    session = models.ForeignKey(
        SurveillanceSession, on_delete=models.CASCADE, db_column='session_id',
        related_name='patient_cases',
    )
    barangay = models.ForeignKey(
        Barangay, on_delete=models.DO_NOTHING, db_column='barangay_id',
    )
    surveillance_report = models.ForeignKey(
        SurveillanceReport, on_delete=models.DO_NOTHING,
        null=True, blank=True, db_column='report_id',
        related_name='patient_case',
    )
    sequence_no = models.PositiveIntegerField(default=1)
    patient_name = models.CharField(max_length=255, default='Unknown Resident')
    civil_status = models.CharField(max_length=50, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    detailed_address = models.TextField(null=True, blank=True)
    is_student = models.BooleanField(default=False)
    grade_year_section = models.CharField(max_length=100, null=True, blank=True)
    school_name = models.CharField(max_length=255, null=True, blank=True)
    age = models.PositiveSmallIntegerField()
    sex = models.CharField(max_length=10, choices=SEX_CHOICES)
    purok_street = models.TextField()
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    date_of_onset = models.DateField(null=True, blank=True)
    symptoms_json = models.TextField()
    symptoms = models.ManyToManyField(Symptom, blank=True, related_name='cases')
    fever_duration = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'patient_cases'
        managed = False

    def __str__(self):
        return f"PatientCase #{self.pk} — Session #{self.session_id}"

    @classmethod
    def normalize_symptoms(cls, symptoms):
        """Validate and dedupe symptom code list from batch payload against PIDSR catalog."""
        if not isinstance(symptoms, (list, tuple)):
            raise ValueError('Symptoms must be a list of indicator codes.')
        active_codes = set(Symptom.objects.values_list('code', flat=True))
        cleaned = normalize_symptom_codes(symptoms)
        for code in cleaned:
            if code not in active_codes and code not in PIDSR_SYMPTOM_CODES:
                raise ValueError(f'Unknown symptom indicator: {code}')
        if not cleaned:
            raise ValueError('At least one symptom indicator is required.')
        return cleaned

    def sync_symptoms_m2m(self, codes):
        """Attach M2M symptom rows and keep ``symptoms_json`` in sync for legacy queries."""
        import json

        symptom_rows = Symptom.objects.filter(code__in=codes)
        self.symptoms.set(symptom_rows)
        self.symptoms_json = json.dumps(codes)
        self.save(update_fields=['symptoms_json'])

    def symptoms_list(self):
        import json
        if self.pk:
            m2m_codes = list(self.symptoms.order_by('code').values_list('code', flat=True))
            if m2m_codes:
                return m2m_codes
        try:
            data = json.loads(self.symptoms_json or '[]')
        except (json.JSONDecodeError, TypeError):
            return []
        return data if isinstance(data, list) else []

    def symptom_labels(self):
        if self.pk and self.symptoms.exists():
            return list(self.symptoms.order_by('name').values_list('name', flat=True))
        label_map = dict(Symptom.objects.filter(
            code__in=self.symptoms_list(),
        ).values_list('code', 'name'))
        return [
            label_map.get(code, PIDSR_SYMPTOM_LABELS.get(code, code))
            for code in self.symptoms_list()
        ]

    @classmethod
    def surveillance_report_ids_for_category(cls, category, barangay_id=None):
        """Return report IDs whose patient case has at least one symptom in the category."""
        groups = SYMPTOM_CATEGORY_GROUP_MAP.get(category)
        if not groups:
            codes = SYMPTOM_CATEGORY_CODES.get(category)
            if not codes:
                return []
            from django.db.models import Q
            symptom_q = Q()
            for code in codes:
                symptom_q |= Q(symptoms_json__contains=f'"{code}"')
            qs = cls.objects.filter(symptom_q).exclude(surveillance_report_id__isnull=True)
            if barangay_id:
                qs = qs.filter(barangay_id=barangay_id)
            return qs.values_list('surveillance_report_id', flat=True).distinct()

        qs = cls.objects.filter(
            symptoms__syndromic_group__in=groups,
        ).exclude(surveillance_report_id__isnull=True).distinct()
        if barangay_id:
            qs = qs.filter(barangay_id=barangay_id)
        return qs.values_list('surveillance_report_id', flat=True).distinct()


# ── Environmental Data (table: environmental_data) ────────────────

class EnvironmentalData(models.Model):
    barangay = models.ForeignKey(
        Barangay, on_delete=models.DO_NOTHING, db_column='barangay_id',
    )
    data_source = models.CharField(max_length=150, null=True, blank=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humidity = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rainfall = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    air_quality_index = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    recorded_at = models.DateTimeField()
    risk_factor_note = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'environmental_data'
        managed = False

    def __str__(self):
        return f"EnvData #{self.pk} — {self.recorded_at}"


# ── Risk Assessments (table: risk_assessments) ────────────────────

class RiskAssessment(models.Model):
    report = models.ForeignKey(
        SurveillanceReport, on_delete=models.DO_NOTHING, db_column='report_id',
    )
    barangay = models.ForeignKey(
        Barangay, on_delete=models.DO_NOTHING, db_column='barangay_id',
    )
    anomaly_score = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    risk_score = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    risk_level = models.CharField(max_length=10, default='low')
    model_version = models.CharField(max_length=50, null=True, blank=True)
    evaluation_status = models.CharField(max_length=10, default='pending')
    evaluated_at = models.DateTimeField(null=True, blank=True)
    recommended_action = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'risk_assessments'
        managed = False

    def __str__(self):
        return f"RiskAssessment #{self.pk} — {self.risk_level}"


# ── Alerts (legacy table: alert_id PK, status column) ─────────────

class Alert(models.Model):
    id = models.AutoField(primary_key=True, db_column='alert_id')
    alert_level = models.CharField(max_length=50)
    alert_date = models.DateTimeField()
    status = models.CharField(max_length=50)
    alert_type = models.CharField(max_length=100)
    analysis_id = models.IntegerField()

    class Meta:
        db_table = 'alerts'
        managed = False

    @property
    def alert_status(self):
        return self.status

    def __str__(self):
        return f"Alert #{self.pk} — {self.alert_level}"


# ── Notification Logs (table: notification_logs) ──────────────────

class NotificationLog(models.Model):
    alert = models.ForeignKey(
        Alert, on_delete=models.DO_NOTHING, db_column='alert_id',
    )
    recipient_role = models.CharField(max_length=30)
    recipient_name = models.CharField(max_length=200, null=True, blank=True)
    channel = models.CharField(max_length=10, default='dashboard')
    message_summary = models.TextField(null=True, blank=True)
    delivery_status = models.CharField(max_length=10, default='sent')
    sent_at = models.DateTimeField()
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'notification_logs'
        managed = False

    def __str__(self):
        return f"Notification #{self.pk} — {self.delivery_status}"


# ── System Logs (table: system_logs) ─────────────────────────────

class SystemLog(models.Model):
    user_role = models.CharField(max_length=50, null=True, blank=True)
    user_id = models.PositiveIntegerField(null=True, blank=True)
    user_display_name = models.CharField(max_length=255, null=True, blank=True)
    activity_type = models.CharField(max_length=100)
    module = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    log_message = models.TextField()
    log_level = models.CharField(max_length=10, default='info')
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'system_logs'
        managed = False

    def __str__(self):
        return f"Log #{self.pk} — {self.activity_type}"


# ── Registration Requests (table: registration_requests) ──────────

class RegistrationRequest(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    suffix = models.CharField(max_length=20, null=True, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    id_type = models.CharField(max_length=50, null=True, blank=True)
    id_number = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(max_length=255)
    contact_number = models.CharField(max_length=20, null=True, blank=True)
    password_hash = models.CharField(max_length=255)
    region_text = models.CharField(max_length=100, null=True, blank=True)
    province_text = models.CharField(max_length=100, null=True, blank=True)
    city_text = models.CharField(max_length=100, null=True, blank=True)
    barangay_text = models.CharField(max_length=100, null=True, blank=True)
    approval_status = models.CharField(max_length=10, default='pending')
    rejection_reason = models.TextField(null=True, blank=True)
    document_path = models.CharField(max_length=500, null=True, blank=True)
    submitted_at = models.DateTimeField()
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        Admin, on_delete=models.DO_NOTHING,
        null=True, blank=True, db_column='reviewed_by',
    )

    class Meta:
        db_table = 'registration_requests'
        managed = False

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.approval_status}"


# ── OCR Results (table: ocr_results) ──────────────────────────────

class OcrResult(models.Model):
    registration = models.OneToOneField(
        RegistrationRequest, on_delete=models.DO_NOTHING, db_column='registration_id',
    )
    extracted_text = models.TextField(null=True, blank=True)
    extracted_name = models.CharField(max_length=255, null=True, blank=True)
    match_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ocr_status = models.CharField(max_length=12)
    processed_at = models.DateTimeField()

    class Meta:
        db_table = 'ocr_results'
        managed = False

    def __str__(self):
        return f"OCR #{self.pk} — {self.ocr_status}"


# ── Login Attempts (table: login_attempts) ────────────────────────

class LoginAttempt(models.Model):
    email = models.EmailField(max_length=255)
    attempted_at = models.DateTimeField()
    success = models.BooleanField(default=False)
    ip_address = models.CharField(max_length=45, null=True, blank=True)

    class Meta:
        db_table = 'login_attempts'
        managed = False

    def __str__(self):
        return f"{self.email} — {'OK' if self.success else 'FAIL'}"


# ── Audit Logs (table: audit_logs) ────────────────────────────────

class AuditLog(models.Model):
    actor_id = models.PositiveIntegerField(null=True, blank=True)
    actor_type = models.CharField(max_length=15, default='admin')
    actor_display_name = models.CharField(max_length=255, null=True, blank=True)
    action = models.CharField(max_length=100)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'audit_logs'
        managed = False

    def __str__(self):
        return f"Audit #{self.pk} — {self.action}"


# ── Field Tasks (table: myapp_fieldtask) ──────────────────────────

class FieldTask(models.Model):
    TASK_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    assigned_to = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='assigned_tasks'
    )
    assigned_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='dispatched_tasks'
    )
    report = models.ForeignKey(
        SurveillanceReport, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='tasks'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='Pending')
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'myapp_fieldtask'
        ordering = ['-created_at']

    def __str__(self):
        return f"Task #{self.pk} - {self.title}"


# ── Legacy / prototype tables (pulse.sql — unused by active PULSE app) ──

class LegacyAdmin(models.Model):
    """Legacy singular ``admin`` table from early schema."""

    id = models.AutoField(primary_key=True, db_column='admin_id')
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50)
    status = models.CharField(max_length=50)

    class Meta:
        db_table = 'admin'
        managed = False


class LegacySuperAdmin(models.Model):
    """Legacy singular ``super_admin`` table from early schema."""

    id = models.AutoField(primary_key=True, db_column='super_admin_id')
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50)
    status = models.CharField(max_length=50)

    class Meta:
        db_table = 'super_admin'
        managed = False


class Bhw(models.Model):
    """Legacy BHW table (superseded by ``users`` with role barangay_health_worker)."""

    id = models.AutoField(primary_key=True, db_column='bhw_id')
    name = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    email = models.EmailField(max_length=254, unique=True)
    contact_info = models.CharField(max_length=100)
    barangay = models.ForeignKey(
        Barangay, on_delete=models.DO_NOTHING, db_column='barangay_id',
    )

    class Meta:
        db_table = 'bhw'
        managed = False


class EnvironmentData(models.Model):
    """Legacy ``environment_data`` table (superseded by ``environmental_data``)."""

    id = models.AutoField(primary_key=True, db_column='environment_id')
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    humidity = models.DecimalField(max_digits=5, decimal_places=2)
    weather_condition = models.CharField(max_length=100)
    recorded_date = models.DateTimeField()
    barangay = models.ForeignKey(
        Barangay, on_delete=models.DO_NOTHING, db_column='barangay_id',
    )

    class Meta:
        db_table = 'environment_data'
        managed = False


class MlAiPrediction(models.Model):
    id = models.AutoField(primary_key=True, db_column='prediction_id')
    disease_type = models.CharField(max_length=100)
    risk_score = models.FloatField()
    prediction_probability = models.FloatField()
    severity_level = models.CharField(max_length=50)
    algorithm_used = models.CharField(max_length=100)
    prediction_date = models.DateTimeField()

    class Meta:
        db_table = 'ml_ai_predictions'
        managed = False


class RiskAnalysis(models.Model):
    id = models.AutoField(primary_key=True, db_column='analysis_id')
    risk_score = models.FloatField()
    anomaly_flag = models.BooleanField()
    analysis_date = models.DateTimeField()
    prediction = models.ForeignKey(
        MlAiPrediction, on_delete=models.DO_NOTHING, db_column='prediction_id',
    )

    class Meta:
        db_table = 'risk_analysis'
        managed = False


class HealthReport(models.Model):
    id = models.AutoField(primary_key=True, db_column='report_id')
    symptoms = models.TextField()
    severity_level = models.CharField(max_length=50)
    report_date = models.DateTimeField()
    admin = models.ForeignKey(
        LegacyAdmin, on_delete=models.DO_NOTHING,
        null=True, blank=True, db_column='admin_id',
    )
    barangay = models.ForeignKey(
        Barangay, on_delete=models.DO_NOTHING, db_column='barangay_id',
    )
    bhw = models.ForeignKey(
        Bhw, on_delete=models.DO_NOTHING, db_column='bhw_id',
    )

    class Meta:
        db_table = 'health_report'
        managed = False


class IncidentReport(models.Model):
    id = models.AutoField(primary_key=True, db_column='incident_id')
    disease_type = models.CharField(max_length=100)
    case_count = models.IntegerField()
    incident_date = models.DateField()
    response_action = models.TextField()
    health_report = models.ForeignKey(
        HealthReport, on_delete=models.DO_NOTHING, db_column='report_id',
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.DO_NOTHING, db_column='patient_id',
    )

    class Meta:
        db_table = 'incident_report'
        managed = False


class HistoricalRecord(models.Model):
    id = models.AutoField(primary_key=True, db_column='record_id')
    disease_type = models.CharField(max_length=100)
    case_status = models.CharField(max_length=50)
    treatment_status = models.CharField(max_length=100)
    date_recorded = models.DateField()
    notes = models.TextField(null=True, blank=True)
    incident = models.ForeignKey(
        IncidentReport, on_delete=models.DO_NOTHING, db_column='incident_id',
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.DO_NOTHING, db_column='patient_id',
    )

    class Meta:
        db_table = 'historical_records'
        managed = False


class LegacyNotification(models.Model):
    """Legacy ``notification`` table (distinct from ``notification_logs``)."""

    id = models.AutoField(primary_key=True, db_column='notification_id')
    recipient_role = models.CharField(max_length=100)
    notification_message = models.TextField()
    sent_date = models.DateTimeField()
    alert = models.ForeignKey(
        Alert, on_delete=models.DO_NOTHING, db_column='alert_id',
    )

    class Meta:
        db_table = 'notification'
        managed = False


# ── Application Sessions (table: sessions) ────────────────────────

class PulseSession(models.Model):
    id = models.CharField(max_length=128, primary_key=True)
    user_id = models.PositiveIntegerField()
    user_type = models.CharField(max_length=15, default='user')
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    invalidated = models.BooleanField(default=False)

    class Meta:
        db_table = 'sessions'
        managed = False

    def __str__(self):
        return f"Session {self.id[:8]}… — {self.user_type}#{self.user_id}"
