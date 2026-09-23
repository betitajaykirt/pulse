from django.test import SimpleTestCase

from reports.ocr_service import (
    parse_lab_fields,
    cross_validate_patient,
    match_test_type,
    match_disease,
    split_person_name,
    apply_record_name_correction,
    infer_lab_outcome,
    resolve_confirm_lab_outcome,
)


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

NEGATIVE_DENGUE_REPORT = """
DENGUE NS1 Ag & IgG/IgM TEST REPORT & CERTIFICATION
Name: AUJERO, JELYN S.
Birthday: 07/18/2005
Age: 21
Gender: FEMALE
Address: PUROK KAPAYAS, BARANGAY POBLACION
Barangay: POBLACION
City: BAGO CITY
Result (List):
DENGUE VIRUS NS1 ANTIGEN: NOT DETECTED
DENGUE IgM ANTIBODY: NOT DETECTED
DENGUE IgG ANTIBODY: NOT DETECTED
Interpretation: NEGATIVE FOR DENGUE FEVER INFECTION
Lab Number: PORT202608-4001
Control Number: LC-2026-N004B21
Certificate Issued: 08/17/2026 14:30
"""

NEGATIVE_COVID_REPORT = """
SARS-CoV-2 RT-PCR LABORATORY REPORT
Name: SANTOS, MARIA L.
Age: 28
Gender: FEMALE
Address: PUROK MABUHAY, BARANGAY POBLACION
Barangay: POBLACION
City: BAGO CITY
Result (List):
SARS-CoV-2 RNA (N gene): NOT DETECTED
SARS-CoV-2 RNA (ORF1ab): NOT DETECTED
Interpretation: NEGATIVE FOR SARS-CoV-2 (COVID-19) INFECTION
Lab Number: PORT202608-4102
Control Number: LC-2026-N00C19
Certificate Issued: 08/18/2026 09:15
"""

NEGATIVE_CULTURE_REPORT = """
BLOOD CULTURE LABORATORY REPORT
Name: SANTOS, MARIA L.
Age: 28
Gender: FEMALE
Result (List):
BLOOD CULTURE: NO GROWTH / SALMONELLA NOT ISOLATED
Interpretation: NEGATIVE FOR TYPHOID AND PARATYPHOID FEVER
Control Number: LC-2026-N00TYP
Certificate Issued: 08/19/2026 11:00
"""


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

PULSE_CITY_LAB_FOOTER = """
ADMINISTRATIVE FOOTER
Lab Number: CHO202609-1001
Control Number: LC-2026-DF001
Certificate Issued: 09/17/2026 10:00
"""

PULSE_CITY_LAB_TABLE_OCR = """
Lab Number Control Number Certificate Issued
CHO202609-1001 LC-2026-DF001 09/17/2026 10:00
"""

PULSE_ENGINE3_OCR = """
BAGO CITY HEALTH OFFICE - CITY HEALTH LABORATORY
PULSE Health Surveillance - Negros Occidental, Philippines
Name: BA�EZ, HERNANI J.
Birthday: 05/21/2004
Age: 28
Gender: MALE
Address: PUROK KAPAYAS, BARANGAY POBLACION
Barangay: POBLACION
City: BAGO CITY
Province: Negros Occidental
Region: Negros Island Region
Lab Number: CHO202609-1001
Control Number: LC-2026-DF001
Certificate Issued: 09/17/2026
10:00
"""

COLUMNAR_DENGUE_RESULTS = """
Analyte / Marker
DENGUE VIRUS NS1 ANTIGEN
DENGUE IgM ANTIBODY
DENGUE IgG ANTIBODY
Result
DETECTED
DETECTED
NOT DETECTED
Interpretation
POSITIVE FOR ACUTE DENGUE FEVER INFECTION
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
        self.assertEqual(fields['first_name'].upper(), 'JELYN')
        self.assertEqual(fields['last_name'].upper(), 'AUJERO')
        self.assertIn('PUROK', fields['address'].upper())
        self.assertNotIn('PURUK', fields['address'].upper())
        self.assertEqual(fields['barangay'].upper(), 'POBLACION')
        self.assertIn('BAGO', fields['city'].upper())

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

    def test_reads_bago_city_lab_footer_identifiers(self):
        fields = parse_lab_fields(PULSE_CITY_LAB_FOOTER)

        self.assertEqual(fields['lab_number'], 'CHO202609-1001')
        self.assertEqual(fields['control_number'], 'LC-2026-DF001')

    def test_reads_identifiers_when_ocr_flattens_footer_table(self):
        fields = parse_lab_fields(PULSE_CITY_LAB_TABLE_OCR)

        self.assertEqual(fields['lab_number'], 'CHO202609-1001')
        self.assertEqual(fields['control_number'], 'LC-2026-DF001')

    def test_pairs_columnar_analytes_with_results_on_the_same_line(self):
        fields = parse_lab_fields(COLUMNAR_DENGUE_RESULTS)

        self.assertEqual(
            fields['lab_results'].splitlines(),
            [
                'DENGUE VIRUS NS1 ANTIGEN: DETECTED',
                'DENGUE IgM ANTIBODY: DETECTED',
                'DENGUE IgG ANTIBODY: NOT DETECTED',
            ],
        )

    def test_city_lab_header_does_not_contaminate_address_fields(self):
        fields = parse_lab_fields(PULSE_ENGINE3_OCR)

        self.assertEqual(fields['raw_patient_name'], 'BA�EZ, HERNANI J')
        self.assertEqual(fields['age'], '28')
        self.assertEqual(fields['city'], 'Bago City')
        self.assertEqual(fields['province'], 'Negros Occidental')
        self.assertEqual(
            fields['address'],
            'Purok Kapayas, Barangay Poblacion, Bago City, Negros Occidental',
        )
        self.assertNotIn('Health Laboratory', fields['address'])

    def test_replacement_character_name_matches_and_uses_record_spelling(self):
        fixed = apply_record_name_correction(
            'BA�EZ, HERNANI J.',
            'Hernani J. Bañez III',
        )

        self.assertTrue(
            cross_validate_patient(
                fixed['raw_patient_name'],
                'Hernani J. Bañez III',
            )['match']
        )
        self.assertEqual(fixed['patient_name'], 'Hernani J. Bañez III')

    def test_fuzzy_name_match_handles_ocr_typo(self):
        result = cross_validate_patient('AUJERO, JELVN S', 'Jelyn S. Aujero')
        self.assertTrue(result['match'])
        self.assertFalse(result['mismatch'])

    def test_test_type_combo(self):
        self.assertEqual(
            match_test_type(SAMPLE_REPORT),
            'Dengue NS1 Ag & IgG/IgM Combo',
        )

    def test_split_last_comma_first(self):
        parts = split_person_name('AUJERO, JELYN S.')
        self.assertEqual(parts['first_name'].upper(), 'JELYN')
        self.assertEqual(parts['last_name'].upper(), 'AUJERO')
        self.assertEqual(parts['middle_name'].replace('.', '').upper(), 'S')

    def test_record_name_corrects_ocr_typo(self):
        fixed = apply_record_name_correction('AUJERO, JELVN S', 'Jelyn S. Aujero')
        self.assertTrue(fixed['name_corrected'])
        self.assertEqual(fixed['first_name'], 'Jelyn')
        self.assertEqual(fixed['last_name'], 'Aujero')
        self.assertIn('JELVN', fixed['raw_patient_name'].upper())

    def test_negative_dengue_report(self):
        fields = parse_lab_fields(NEGATIVE_DENGUE_REPORT)
        self.assertEqual(fields['overview']['verdict'], 'NEGATIVE')
        self.assertEqual(fields['lab_outcome'], 'negative')
        self.assertIn('NEGATIVE FOR DENGUE', fields['interpretation'])
        self.assertIn('NS1 ANTIGEN: NOT DETECTED', fields['lab_results'])
        self.assertIn('IgM ANTIBODY: NOT DETECTED', fields['lab_results'])
        self.assertIn('IgG ANTIBODY: NOT DETECTED', fields['lab_results'])
        self.assertEqual(fields['overview']['marker_summary'], 'NS1(-) / IgM(-) / IgG(-)')
        self.assertFalse(any(m['positive'] for m in fields['markers']))
        self.assertEqual(match_disease(NEGATIVE_DENGUE_REPORT), 'Dengue Fever')
        self.assertEqual(infer_lab_outcome(fields['interpretation'], fields['markers']), 'negative')

    def test_negative_covid_pcr_report(self):
        fields = parse_lab_fields(NEGATIVE_COVID_REPORT)
        self.assertEqual(fields['lab_outcome'], 'negative')
        self.assertEqual(fields['overview']['verdict'], 'NEGATIVE')
        self.assertIn('NEGATIVE FOR SARS-COV-2', fields['interpretation'].upper())
        self.assertTrue(any('NOT DETECTED' in m['status'] for m in fields['markers']))
        self.assertFalse(any(m['positive'] for m in fields['markers']))
        self.assertEqual(match_disease(NEGATIVE_COVID_REPORT), 'COVID-19')
        self.assertEqual(match_test_type(NEGATIVE_COVID_REPORT), 'PCR')

    def test_negative_culture_no_growth(self):
        fields = parse_lab_fields(NEGATIVE_CULTURE_REPORT)
        self.assertEqual(fields['lab_outcome'], 'negative')
        self.assertIn('NEGATIVE FOR TYPHOID', fields['interpretation'])
        statuses = ' '.join(m['status'] for m in fields['markers'])
        self.assertTrue('NO GROWTH' in statuses or 'NOT ISOLATED' in statuses)
        self.assertEqual(match_disease(NEGATIVE_CULTURE_REPORT), 'Typhoid and Paratyphoid Fever')
        self.assertEqual(match_test_type(NEGATIVE_CULTURE_REPORT), 'Culture')

    def test_unclear_lab_stays_blocked(self):
        self.assertEqual(resolve_confirm_lab_outcome('', ''), '')
        self.assertEqual(resolve_confirm_lab_outcome('Pending culture', 'See remarks'), '')
        self.assertEqual(
            resolve_confirm_lab_outcome('Inconclusive', '',),
            '',
        )

    def test_confirm_outcome_reads_interpretation_not_posted_positive(self):
        self.assertEqual(
            resolve_confirm_lab_outcome('NEGATIVE FOR DENGUE FEVER INFECTION', ''),
            'negative',
        )
        self.assertEqual(
            resolve_confirm_lab_outcome('POSITIVE FOR ACUTE DENGUE FEVER INFECTION', ''),
            'positive',
        )
        self.assertEqual(
            resolve_confirm_lab_outcome('', 'DENGUE VIRUS NS1 ANTIGEN: NOT DETECTED'),
            'negative',
        )
