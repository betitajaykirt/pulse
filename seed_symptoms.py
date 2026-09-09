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
    from mysite.command_safety import assert_safe_for_destructive_commands, load_project_env
    load_project_env()
    assert_safe_for_destructive_commands('seed_symptoms.py')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    django.setup()

    from myapp.symptom_data import seed_all_symptoms

    seed_all_symptoms()
