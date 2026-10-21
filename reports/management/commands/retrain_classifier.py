"""Nightly retrain of the disease-classification Random Forest.

Trains on historical_training_data.csv plus lab-confirmed live cases, compares the
result with the model it would replace on held-out cases, and saves it only when it
is at least as accurate. Run by hand with ``python manage.py retrain_classifier``.
"""
import time

import pandas as pd
from django.core.management.base import BaseCommand
from sklearn.model_selection import train_test_split

from ml_engine import TARGET_COLUMN, _prepare_feature_frame, fit_random_forest_classifier
from reports.classifier_store import load_active_model, pack_model, save_active_model
from reports.prediction_service import load_csv_training_frame, load_live_training_frame

DEFAULT_MIN_LIVE_CASES = 10
HOLDOUT_FRACTION = 0.2
RANDOM_STATE = 42


def holdout_accuracy(classifier, label_encoder, frame: pd.DataFrame) -> float:
    """Share of held-out rows whose disease the model gets right."""
    predicted = label_encoder.inverse_transform(classifier.predict(_prepare_feature_frame(frame)))
    actual = frame[TARGET_COLUMN].astype(str).str.strip().to_numpy()
    return float((predicted == actual).mean())


def split_holdout(frame: pd.DataFrame, fraction: float = HOLDOUT_FRACTION):
    labels = frame[TARGET_COLUMN].astype(str).str.strip()
    stratify = labels if labels.value_counts().min() >= 2 else None
    return train_test_split(frame, test_size=fraction, random_state=RANDOM_STATE, stratify=stratify)


class Command(BaseCommand):
    help = 'Retrain the Random Forest on the CSV plus lab-confirmed live cases (nightly job).'

    def add_arguments(self, parser):
        parser.add_argument('--min-live', type=int, default=DEFAULT_MIN_LIVE_CASES,
                            help='Skip retraining below this many lab-confirmed live cases.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Train and compare, but do not save anything.')

    def handle(self, *args, **options):
        started = time.monotonic()
        base = load_csv_training_frame()
        live = load_live_training_frame(base.columns)
        live_rows = 0 if live is None else len(live)
        self.stdout.write(f'CSV rows: {len(base)}. Lab-confirmed live cases: {live_rows}.')

        if live_rows < options['min_live']:
            self.stdout.write(self.style.WARNING(
                f'Not retraining: need at least {options["min_live"]} lab-confirmed live cases '
                f'(found {live_rows}). The current model stays active.'
            ))
            return

        combined = base if live is None else pd.concat([base, live], ignore_index=True)
        train, holdout = split_holdout(combined)

        candidate = fit_random_forest_classifier(train)
        candidate_accuracy = holdout_accuracy(*candidate, holdout)

        active = load_active_model()
        if active:
            reference = (active[1], active[2])
            reference_name = f'active model #{active[0]}'
        else:
            csv_only = train[~train.index.isin(range(len(base), len(combined)))]
            reference = fit_random_forest_classifier(csv_only)
            reference_name = 'CSV-only baseline'
        reference_accuracy = holdout_accuracy(*reference, holdout)

        self.stdout.write(
            f'Holdout ({len(holdout)} rows): candidate {candidate_accuracy:.4f} '
            f'vs {reference_name} {reference_accuracy:.4f}.'
        )

        if candidate_accuracy < reference_accuracy:
            self.stdout.write(self.style.WARNING('Candidate is less accurate. Keeping the current model.'))
            return

        final = fit_random_forest_classifier(combined)
        size_mb = len(pack_model(*final)) / 1_048_576
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'Dry run: candidate would be saved (about {size_mb:.1f} MB). Nothing written.'
            ))
            return

        row = save_active_model(
            *final,
            accuracy=candidate_accuracy,
            reference_accuracy=reference_accuracy,
            base_rows=len(base),
            live_rows=live_rows,
            notes=f'Compared with {reference_name}.',
        )
        self.stdout.write(self.style.SUCCESS(
            f'Saved classifier #{row.id} ({size_mb:.1f} MB) in {time.monotonic() - started:.0f}s. '
            'Web workers pick it up within an hour.'
        ))
