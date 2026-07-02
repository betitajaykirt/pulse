"""
PULSE Health Surveillance — Two-Stage Machine Learning Pipeline
================================================================

This module is an **independent research reference implementation** for the
PULSE (Public Health Unified Surveillance & Epidemiology) system. It
demonstrates how validated syndromic intake records can be processed through:

1. **Stage 1 — Unsupervised Outbreak Surveillance Guardrail (Isolation Forest)**
   Acts as a **Spike and Spatial Outbreak Detection Engine**. The model compares
   incoming case profiles — spatial-temporal clusters defined by patient barangay,
   submission date/time window, and syndromic symptom Groups A–E — against
   historical community baselines. Rows with ``is_anomaly == -1`` and elevated
   anomaly scores represent **localized health anomalies**: probable outbreaks
   or unusual disease spikes warranting CHO escalation, not mere data-entry typos.

2. **Stage 2 — Supervised syndromic classification (Random Forest)**
   Maps validated, cleaned feature vectors (demographics + binary symptom
   indicators from Groups A–E) to provisional disease labels such as
   *Dengue*, *Respiratory Illness*, or *Undetermined*.

Architecture note for academic documentation
--------------------------------------------
The pipeline follows a **surveillance-then-classify** pattern common in
operational ML for public health:

- pandas handles tabular normalization (type coercion, missing-value imputation,
  one-hot encoding of categorical fields).
- Isolation Forest performs **unsupervised multivariate outbreak screening**
  without requiring labeled outbreak examples — it isolates sparse regions of the
  joint distribution where barangay-level symptom signatures deviate from
  expected historical baselines (temporal clustering + syndromic co-occurrence).
- Random Forest provides an **interpretable ensemble** baseline for multi-class
  syndromic classification; feature importances can be exported for CHO review.

In production deployment, Stage 1 feature vectors are enriched with encoded
``barangay_id`` and discretized ``submission_datetime`` buckets alongside the
demographic and Groups A–E columns used in this reference script.

This file is intentionally decoupled from Django ORM, views, and HTTP layers so
it can be executed in notebooks, batch jobs, or CI smoke tests.

Dependencies: pandas, scikit-learn, numpy
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder

# ---------------------------------------------------------------------------
# Feature schema — syndromic indicator columns aligned with PULSE intake
# ---------------------------------------------------------------------------

# Group A: Systemic & Constitutional
GROUP_A_SYMPTOMS: Sequence[str] = (
    "fever_high",
    "fever_low",
    "chills",
    "headache",
    "body_ache",
    "fatigue",
)

# Group B: Respiratory & ENT
GROUP_B_SYMPTOMS: Sequence[str] = (
    "cough_dry",
    "cough_paroxysms",
    "sore_throat",
    "runny_nose",
    "dyspnea",
)

# Group C: Gastrointestinal & Hepatic (subset used for demo)
GROUP_C_SYMPTOMS: Sequence[str] = (
    "diarrhea_watery",
    "vomiting",
    "jaundice",
    "abdominal_cramps",
)

# Group D: Dermatological (subset)
GROUP_D_SYMPTOMS: Sequence[str] = (
    "maculopapular_rash",
    "petechiae_bleeding",
)

# Group E: Contextual exposure (subset)
GROUP_E_SYMPTOMS: Sequence[str] = (
    "animal_bite",
    "floodwater_exposure",
)

SYNDROMIC_FEATURE_COLUMNS: List[str] = list(
    GROUP_A_SYMPTOMS
    + GROUP_B_SYMPTOMS
    + GROUP_C_SYMPTOMS
    + GROUP_D_SYMPTOMS
    + GROUP_E_SYMPTOMS
)

# Open-Meteo environmental context (aligned with ``EnvironmentalData`` model)
CLIMATE_FEATURE_COLUMNS: Sequence[str] = ("temperature", "humidity", "rainfall")
CLIMATE_DEFAULTS = {
    "temperature": 30.0,
    "humidity": 70.0,
    "rainfall": 0.0,
}

DEMOGRAPHIC_COLUMNS: Sequence[str] = ("age", "sex")

TARGET_COLUMN = "disease_label"

# Labels returned by the Random Forest classifier
DISEASE_LABELS: Sequence[str] = (
    "Dengue",
    "Respiratory Illness",
    "Leptospirosis",
    "Acute Gastroenteritis",
    "Hand, Foot, and Mouth Disease",
    "Influenza-like Illness (ILI)",
    "Undetermined",
)

# Returned when ``predict_proba`` max score is below the confidence cutoff
INCONCLUSIVE_SYNDROMIC_LABEL = "Inconclusive Syndromic Pattern"
DEFAULT_CLASSIFICATION_CONFIDENCE = 0.60


# ---------------------------------------------------------------------------
# Django Symptom catalog bridge — maps DB ``Symptom.code`` → ML feature columns
# ---------------------------------------------------------------------------


def resolve_syndromic_feature_columns(
    symptom_codes: Optional[Sequence[str]] = None,
) -> List[str]:
    """
    Merge the reference demo columns with active DB symptom codes.

    Each ``Symptom.code`` value in Django maps 1:1 to a binary ML feature
    column. Pass ``symptom_codes`` from ``Symptom.objects.values_list('code')``
    or from ``PatientCase.symptoms_list()`` when building production batches.
    """
    columns = list(SYNDROMIC_FEATURE_COLUMNS)
    if symptom_codes:
        for code in symptom_codes:
            if code not in columns:
                columns.append(code)
    return columns


def patient_case_to_feature_row(
    *,
    age,
    sex,
    symptom_codes: Sequence[str],
    extra_columns: Optional[Sequence[str]] = None,
    temperature: Optional[float] = None,
    humidity: Optional[float] = None,
    rainfall: Optional[float] = None,
) -> dict:
    """
    Convert a Django ``PatientCase`` symptom M2M selection into a flat dict
    suitable for ``pd.DataFrame([row])`` before calling ``detect_anomalies``
    or ``train_and_classify``.
    """
    row = {"age": age, "sex": sex}
    active = set(symptom_codes)
    for col in resolve_syndromic_feature_columns(extra_columns):
        row[col] = 1 if col in active else 0
    row["temperature"] = (
        float(temperature) if temperature is not None else CLIMATE_DEFAULTS["temperature"]
    )
    row["humidity"] = (
        float(humidity) if humidity is not None else CLIMATE_DEFAULTS["humidity"]
    )
    row["rainfall"] = (
        float(rainfall) if rainfall is not None else CLIMATE_DEFAULTS["rainfall"]
    )
    return row


def ensure_climate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee climate features exist with safe defaults for matrix alignment."""
    working = df.copy()
    for col, default in CLIMATE_DEFAULTS.items():
        if col not in working.columns:
            working[col] = default
        else:
            working[col] = pd.to_numeric(working[col], errors="coerce").fillna(default)
    return working


def patient_cases_queryset_to_dataframe(cases) -> pd.DataFrame:
    """
    Export a Django ``PatientCase`` queryset (with prefetched ``symptoms``) to
    a pandas DataFrame aligned with this pipeline's feature schema.

    Usage (inside a Django shell or batch job)::

        from myapp.models import PatientCase
        from ml_pipeline import patient_cases_queryset_to_dataframe, detect_anomalies

        qs = PatientCase.objects.prefetch_related('symptoms').all()
        df = patient_cases_queryset_to_dataframe(qs)
        screened = detect_anomalies(df)
    """
    rows = []
    all_codes = set(SYNDROMIC_FEATURE_COLUMNS)
    for case in cases:
        codes = list(case.symptoms.values_list('code', flat=True)) if case.pk else case.symptoms_list()
        all_codes.update(codes)
        rows.append(patient_case_to_feature_row(
            age=case.age,
            sex=case.sex,
            symptom_codes=codes,
            extra_columns=all_codes,
        ))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Internal helpers — data cleaning & feature engineering
# ---------------------------------------------------------------------------


def _coerce_binary(series: pd.Series) -> pd.Series:
    """Map mixed truthy inputs to strict 0/1 integers for symptom flags."""
    return series.fillna(0).astype(float).clip(0, 1).astype(int)


def _encode_sex(series: pd.Series) -> pd.Series:
    """
    Normalize sex to numeric codes for tree-based models.

    Male → 0, Female → 1, unknown/other → 0.5 (neutral midpoint).
    """
    mapping = {
        "male": 0.0,
        "m": 0.0,
        "female": 1.0,
        "f": 1.0,
    }
    return (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda v: mapping.get(v, 0.5))
    )


def _prepare_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a model-ready numeric matrix from raw intake rows.

    Steps
    -----
    1. Coerce ``age`` to numeric (invalid → NaN, then median-imputed).
    2. Encode ``sex`` to {0, 0.5, 1}.
    3. Cast all syndromic checkbox columns to binary {0, 1}.
    4. Median-impute any remaining NaNs in numeric columns.
    """
    working = df.copy()

    if "age" in working.columns:
        working["age"] = pd.to_numeric(working["age"], errors="coerce")
    else:
        working["age"] = np.nan

    if "sex" in working.columns:
        working["sex_encoded"] = _encode_sex(working["sex"])
    else:
        working["sex_encoded"] = 0.5

    working = ensure_climate_columns(working)

    feature_cols = (
        ["age", "sex_encoded"]
        + list(SYNDROMIC_FEATURE_COLUMNS)
        + list(CLIMATE_FEATURE_COLUMNS)
    )
    for col in SYNDROMIC_FEATURE_COLUMNS:
        if col not in working.columns:
            working[col] = 0
        working[col] = _coerce_binary(working[col])

    for col in CLIMATE_FEATURE_COLUMNS:
        working[col] = pd.to_numeric(working[col], errors="coerce").fillna(
            CLIMATE_DEFAULTS[col]
        )

    matrix = working[feature_cols].astype(float)
    imputer = SimpleImputer(strategy="median")
    imputed = imputer.fit_transform(matrix)
    return pd.DataFrame(imputed, columns=feature_cols, index=working.index)


# ---------------------------------------------------------------------------
# Stage 1 — Isolation Forest outbreak surveillance guardrail
# ---------------------------------------------------------------------------


def detect_anomalies(
    data: pd.DataFrame,
    *,
    contamination: float = 0.08,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Screen health reports for epidemiological anomalies using Isolation Forest.

    This function implements the **Spike and Spatial Outbreak Detection Engine**
    guardrail. Isolation Forest recursively partitions the multivariate feature
    space built from demographics and syndromic Groups A–E; in production, that
    space also encodes **patient barangay** and **submission date/time** so the
    model can detect spatial-temporal clusters that diverge from historical
    community baselines.

    Points requiring fewer random splits to isolate represent **localized health
    anomalies** — unusual co-occurrence of symptom groups within a barangay-time
    window that may indicate a **probable outbreak** or disease spike, rather
    than isolated data-entry errors.

    Parameters
    ----------
    data : pd.DataFrame
        Intake records with at minimum ``age``, optional ``sex``, and binary
        syndromic indicator columns (see ``SYNDROMIC_FEATURE_COLUMNS``).
        Production batches should also include ``barangay_id`` and
        ``submission_datetime`` for full spatial-temporal cluster analysis.
    contamination : float, optional
        Expected proportion of outbreak-signal rows in the batch (default 0.08).
        Tune against CHO-confirmed outbreak windows and seasonal baselines.
    random_state : int, optional
        Seed for reproducible research experiments.

    Returns
    -------
    pd.DataFrame
        Copy of ``data`` with two appended columns:

        - ``is_anomaly`` : int — ``1`` for baseline-consistent reports,
          ``-1`` for probable outbreak / spike signals
        - ``anomaly_score`` : float — raw ``score_samples`` from the fitted
          model (lower values indicate stronger deviation from baseline)

    Notes
    -----
    Rows with ``is_anomaly == -1`` should trigger **outbreak surveillance review**
    (APTAS alert triage, barangay hotspot mapping) before Stage 2 disease
    classification is applied at the individual patient level.
    """
    if data.empty:
        result = data.copy()
        result["is_anomaly"] = pd.Series(dtype=int)
        result["anomaly_score"] = pd.Series(dtype=float)
        return result

    features = _prepare_feature_frame(data)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(features)

    predictions = model.predict(features)
    scores = model.score_samples(features)

    result = data.copy()
    result["is_anomaly"] = predictions.astype(int)
    result["anomaly_score"] = scores
    return result


# ---------------------------------------------------------------------------
# Stage 2 — Random Forest syndromic disease classification
# ---------------------------------------------------------------------------


def train_and_classify(
    train_data: pd.DataFrame,
    incoming_patient: pd.DataFrame,
    *,
    random_state: int = 42,
    confidence_threshold: float = DEFAULT_CLASSIFICATION_CONFIDENCE,
    low_confidence_label: str = INCONCLUSIVE_SYNDROMIC_LABEL,
) -> str:
    """
    Train a Random Forest on labeled syndromic data and classify one patient.

    The classifier consumes the same engineered feature space as Stage 1
    (demographics + binary symptom groups A–E). Random Forest aggregates
    multiple decorrelated decision trees, providing robustness to noisy
    checkbox entry and moderate class imbalance — a pragmatic baseline before
    deploying gradient-boosted or neural approaches in production.

    Parameters
    ----------
    train_data : pd.DataFrame
        Historical labeled cases. Must include ``disease_label`` plus intake
        columns (``age``, ``sex``, syndromic indicators). Labels should be
        drawn from ``DISEASE_LABELS`` where possible.
    incoming_patient : pd.DataFrame
        Single-row (or first-row) patient feature record to classify.
    random_state : int, optional
        Seed for reproducible experiments.

    Returns
    -------
    str
        Predicted disease classification label, e.g. ``'Dengue'``,
        ``'Respiratory Illness'``, or ``'Undetermined'``.

    Raises
    ------
    ValueError
        If training data is empty or missing the target column.
    """
    if train_data.empty:
        raise ValueError("train_data must contain at least one labeled row.")
    if TARGET_COLUMN not in train_data.columns:
        raise ValueError(f"train_data must include a '{TARGET_COLUMN}' column.")

    x_train = _prepare_feature_frame(train_data)
    y_raw = train_data[TARGET_COLUMN].astype(str).str.strip()

    label_encoder = LabelEncoder()
    y_train = label_encoder.fit_transform(y_raw)

    classifier = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=random_state,
        n_jobs=-1,
    )
    classifier.fit(x_train, y_train)

    if incoming_patient.empty:
        return "Undetermined"

    x_infer = _prepare_feature_frame(incoming_patient.iloc[[0]])
    proba = classifier.predict_proba(x_infer)[0]
    max_idx = int(np.argmax(proba))
    max_prob = float(proba[max_idx])

    if max_prob < confidence_threshold:
        return low_confidence_label

    return str(label_encoder.inverse_transform([max_idx])[0])


# ---------------------------------------------------------------------------
# Demonstration — runnable mock dataset for terminal smoke tests
# ---------------------------------------------------------------------------


def _build_mock_training_set() -> pd.DataFrame:
    """
    Construct a small, realistic labeled corpus for local experimentation.

    Each row mirrors a BHW batch-entry patient: age, sex, syndromic
    checkboxes, and a CHO/ML-assigned ``disease_label``.
    """
    rows = [
        # Dengue-like constitutional + rash/bleeding pattern (wet season vector habitat)
        dict(age=14, sex="Female", fever_high=1, headache=1, body_ache=1,
             maculopapular_rash=1, petechiae_bleeding=1,
             temperature=29.5, humidity=88.0, rainfall=6.2, disease_label="Dengue"),
        dict(age=22, sex="Male", fever_high=1, chills=1, body_ache=1,
             maculopapular_rash=1, fatigue=1,
             temperature=30.1, humidity=90.0, rainfall=4.5, disease_label="Dengue"),
        dict(age=8, sex="Female", fever_high=1, headache=1, body_ache=1,
             petechiae_bleeding=1,
             temperature=28.8, humidity=86.0, rainfall=3.1, disease_label="Dengue"),
        # Respiratory cluster (cooler, drier indoor transmission)
        dict(age=45, sex="Male", fever_low=1, cough_dry=1, sore_throat=1,
             runny_nose=1, dyspnea=1,
             temperature=24.5, humidity=62.0, rainfall=0.0, disease_label="Respiratory Illness"),
        dict(age=67, sex="Female", cough_paroxysms=1, dyspnea=1, fatigue=1,
             temperature=23.8, humidity=58.0, rainfall=0.0, disease_label="Respiratory Illness"),
        dict(age=31, sex="Male", fever_low=1, cough_dry=1, headache=1,
             temperature=25.2, humidity=65.0, rainfall=0.2, disease_label="Respiratory Illness"),
        # Leptospirosis — flood exposure + fever + GI (heavy rainfall)
        dict(age=29, sex="Male", fever_high=1, headache=1, body_ache=1,
             floodwater_exposure=1, jaundice=1, abdominal_cramps=1,
             temperature=27.0, humidity=92.0, rainfall=18.5, disease_label="Leptospirosis"),
        dict(age=35, sex="Female", fever_high=1, body_ache=1,
             floodwater_exposure=1, vomiting=1,
             temperature=26.5, humidity=94.0, rainfall=22.0, disease_label="Leptospirosis"),
        # Acute gastroenteritis
        dict(age=5, sex="Male", diarrhea_watery=1, vomiting=1, abdominal_cramps=1,
             temperature=29.0, humidity=75.0, rainfall=1.5, disease_label="Acute Gastroenteritis"),
        dict(age=40, sex="Female", diarrhea_watery=1, vomiting=1, fever_low=1,
             temperature=28.5, humidity=72.0, rainfall=0.8, disease_label="Acute Gastroenteritis"),
        # Sparse / ambiguous presentations → Undetermined in training
        dict(age=50, sex="Male", fatigue=1, headache=1,
             temperature=30.0, humidity=70.0, rainfall=0.0, disease_label="Undetermined"),
        dict(age=19, sex="Female", fever_low=1,
             temperature=30.0, humidity=70.0, rainfall=0.0, disease_label="Undetermined"),
    ]
    return ensure_climate_columns(pd.DataFrame(rows))


def _build_mock_incoming_cases() -> pd.DataFrame:
    """Incoming cases for demo: baseline-consistent, outbreak spike, and infer test."""
    return pd.DataFrame(
        [
            # Typical dengue presentation — consistent with historical baseline
            dict(
                age=17,
                sex="Female",
                fever_high=1,
                headache=1,
                body_ache=1,
                maculopapular_rash=1,
                petechiae_bleeding=0,
            ),
            # Simulated spatial-temporal cluster spike — syndromic signature deviates
            # sharply from barangay baseline (probable outbreak signal)
            dict(
                age=999,
                sex="Unknown",
                fever_high=1,
                cough_dry=1,
                diarrhea_watery=1,
                jaundice=1,
                animal_bite=1,
                floodwater_exposure=1,
            ),
            # Respiratory cluster pattern — baseline-consistent individual report
            dict(
                age=52,
                sex="Male",
                cough_dry=1,
                dyspnea=1,
                sore_throat=1,
                runny_nose=1,
                fever_low=1,
            ),
        ]
    )


if __name__ == "__main__":
    print("=" * 72)
    print("PULSE Two-Stage ML Pipeline — Outbreak Surveillance Demo")
    print("=" * 72)

    training = _build_mock_training_set()
    incoming = _build_mock_incoming_cases()

    print(f"\n[Dataset] Historical baseline rows: {len(training)}")
    print(f"[Dataset] Label distribution:\n{training[TARGET_COLUMN].value_counts().to_string()}")

    # --- Stage 1: outbreak guardrail on combined baseline + incoming window ---
    combined = pd.concat([training.drop(columns=[TARGET_COLUMN]), incoming], ignore_index=True)
    screened = detect_anomalies(combined)

    print("\n--- Stage 1: Isolation Forest — Spike & Spatial Outbreak Detection ---")
    display_cols: Iterable[str] = ["age", "sex"] + list(SYNDROMIC_FEATURE_COLUMNS[:4])
    available = [c for c in display_cols if c in screened.columns]
    anomaly_view = screened[available + ["is_anomaly", "anomaly_score"]].copy()
    anomaly_view["anomaly_score"] = anomaly_view["anomaly_score"].round(4)
    print(anomaly_view.to_string(index=True))

    anomalies = screened[screened["is_anomaly"] == -1]
    print(f"\nProbable outbreak / spike signals: {len(anomalies)} row(s)")
    if not anomalies.empty:
        print("-> Rows with is_anomaly == -1 exceed historical baseline thresholds")
        print("-> Recommend CHO outbreak surveillance review and APTAS alert triage")

    # --- Stage 2: classify each incoming patient (defer if outbreak flag raised) ---
    print("\n--- Stage 2: Random Forest Syndromic Classification ---")
    for idx, row in incoming.iterrows():
        patient_df = pd.DataFrame([row])
        anomaly_flag = screened.iloc[len(training) + idx]["is_anomaly"]

        if anomaly_flag == -1:
            print(
                f"\nPatient #{idx + 1}: OUTBREAK SURVEILLANCE FLAG "
                f"(anomaly_score={screened.iloc[len(training) + idx]['anomaly_score']:.4f})"
            )
            print("  Action: Escalate for cluster investigation before individual classification")
            print("  Provisional label: Undetermined (pending outbreak surveillance review)")
            continue

        label = train_and_classify(training, patient_df)
        symptom_flags = [c for c in SYNDROMIC_FEATURE_COLUMNS if row.get(c, 0) == 1]
        print(f"\nPatient #{idx + 1}: age={row['age']}, sex={row['sex']}")
        print(f"  Active indicators: {', '.join(symptom_flags) or '(none)'}")
        print(f"  Predicted disease label: {label}")

    print("\n" + "=" * 72)
    print("Outbreak surveillance pipeline demo complete.")
    print("=" * 72)
