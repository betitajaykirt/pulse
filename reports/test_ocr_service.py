from django.test import SimpleTestCase

from reports.ocr_service import parse_lab_fields, cross_validate_patient, match_test_type


SAMPLE_REPORT = """
DENGUE NS1 Ag & IgG/IgM TEST REPORT & CERTIFICATION
Name: AUJERO, JELYN S.
Birthday: 07/18/2005
Age: 21
Nationality: PHILIPPINES
Civil Status: SINGLE
Gender: FEMALE
Passport/ID No: NA
Address: PURUK KAPAYAS, BARANGAY POBLACION
Barangay: POBLACION
City: BAGO CITY
Result (List):
DENGUE VIRUS NS1 ANTIGEN: DETECTED
DENGUE IgM ANTIBODY: DETECTED
DENGUE IgG ANTIBODY: NOT DETECTED
Interpretation: POSITIVE FOR ACUTE DENGUE FEVER INFECTION
Remarks: NS1 and IgM positivity confirms an acute primary infection.
Lab Number: PORT202608-3882
Control Number: LC-2026-004B21
Certificate Issued: 08/17/2026 14:30
"""

MESSY_OCR = """
Name AUJERO, JELVN S Age: 21 Gender FEMALE
Address PURUK KAPAYAS Barangay POBLACION
DENGUE VIRUS NS1 ANTIGEN DETECTED
DENGUE IgM ANTIBODY DETECTED
DENGUE IgG ANTIBODY NOT DETECTED
POSITIVE FOR ACUTE DENGUE FEVER INFECTION
Lab Number Control Number
PORT202608-3882 LC-2026-004B21
Certificate Issued 08/17/2026 14:30
"""

SWAPPED_LABELS = """
Name: AUJERO, JELYN S
Lab Number: Control
Control Number: PORT202608-3882
Certificate Issued: 08/17/2026 14:30
NS1 ANTIGEN: DETECTED
IgM ANTIBODY: DETECTED
IgG ANTIBODY: NOT DETECTED
Interpretation POSITIVE FOR ACUTE DENGUE FEVER INFECTION
"""


class ParseLabFieldsTests(SimpleTestCase):
    def test_clean_red_cross_report(self):
        fields = parse_lab_fields(SAMPLE_REPORT)
        self.assertIn('AUJERO', fields['patient_name'].upper())
        self.assertEqual(fields['age'], '21')
        self.assertEqual(fields['sex'], 'FEMALE')
        self.assertIn('KAPAYAS', fields['address'].upper())
        self.assertEqual(fields['lab_number'], 'PORT202608-3882')
        self.assertEqual(fields['control_number'], 'LC-2026-004B21')
        self.assertIn('08/17/2026', fields['result_date'])
        self.assertIn('NS1 ANTIGEN: DETECTED', fields['lab_results'])
        self.assertIn('IgM ANTIBODY: DETECTED', fields['lab_results'])
        self.assertIn('IgG ANTIBODY: NOT DETECTED', fields['lab_results'])
        self.assertIn('POSITIVE FOR ACUTE DENGUE', fields['interpretation'])
        self.assertEqual(fields['overview']['verdict'], 'POSITIVE')
        self.assertEqual(fields['overview']['marker_summary'], 'NS1(+) / IgM(+) / IgG(-)')

    def test_messy_ocr_still_recovers_fields(self):
        fields = parse_lab_fields(MESSY_OCR)
        self.assertEqual(fields['lab_number'], 'PORT202608-3882')
        self.assertEqual(fields['control_number'], 'LC-2026-004B21')
        self.assertIn('08/17/2026', fields['result_date'])
        self.assertIn('DETECTED', fields['lab_results'])
        self.assertIn('POSITIVE', fields['interpretation'])

    def test_rejects_control_as_specimen_and_swaps_port(self):
        fields = parse_lab_fields(SWAPPED_LABELS)
        self.assertNotEqual(fields['lab_number'].lower(), 'control')
        self.assertEqual(fields['lab_number'], 'PORT202608-3882')

    def test_fuzzy_name_match_handles_ocr_typo(self):
        result = cross_validate_patient('AUJERO, JELVN S', 'Jelyn S. Aujero')
        self.assertTrue(result['match'])
        self.assertFalse(result['mismatch'])

    def test_test_type_combo(self):
        self.assertEqual(
            match_test_type(SAMPLE_REPORT),
            'Dengue NS1 Ag & IgG/IgM Combo',
        )
