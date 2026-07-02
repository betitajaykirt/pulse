#!/usr/bin/env python
"""
Seed Django reference catalogs (symptoms + mitigation protocols).

Usage (from djangotutorial/):
    python seed_reference_data.py
"""
import os
import sys

import django

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    django.setup()

    from myapp.symptom_data import seed_all_symptoms
    from myapp.mitigation_data import seed_mitigation_protocols
    from myapp.threshold_data import seed_disease_category_thresholds

    print('=== PULSE-AI Reference Data Seed ===')
    seed_all_symptoms()
    seed_mitigation_protocols()
    seed_disease_category_thresholds()
    print('=== Seed complete ===')
