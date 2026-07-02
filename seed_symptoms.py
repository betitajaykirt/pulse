#!/usr/bin/env python
"""
Seed the dynamic Symptom catalog for PULSE-AI intake and ML export.

Usage (from djangotutorial/):
    python seed_symptoms.py

Also invoked automatically by migration ``0007_symptom_model``.
"""
import os
import sys

import django

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    django.setup()

    from myapp.symptom_data import seed_all_symptoms

    seed_all_symptoms()
