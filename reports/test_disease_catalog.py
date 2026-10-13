from django.test import SimpleTestCase

from reports.disease_catalog import clean_new_symptoms, code_for_new_symptom, validate_added_disease


class AddedDiseaseValidationTests(SimpleTestCase):
    def test_rejects_a_disease_the_model_already_knows(self):
        with self.assertRaises(ValueError):
            validate_added_disease('Dengue Fever', 'Category 2', ['fever'])

    def test_accepts_a_new_name_with_checklist_symptoms(self):
        name, category, codes = validate_added_disease(
            '  Nipah Virus ',
            'Category 1',
            ['fever', 'headache', 'fever'],
        )
        self.assertEqual(name, 'Nipah Virus')
        self.assertEqual(category, 'Category 1')
        self.assertEqual(codes, ['fever', 'headache'])

    def test_requires_a_symptom(self):
        with self.assertRaises(ValueError):
            validate_added_disease('Nipah Virus', 'Category 1', [])

    def test_accepts_an_office_added_symptom_code(self):
        name, category, codes = validate_added_disease(
            'Nipah Virus',
            'Category 1',
            ['added_swollen_lymph_nodes'],
            extra_allowed_codes=['added_swollen_lymph_nodes'],
        )
        self.assertEqual((name, category, codes), ('Nipah Virus', 'Category 1', ['added_swollen_lymph_nodes']))

    def test_rejects_a_symptom_already_on_the_checklist(self):
        with self.assertRaises(ValueError):
            clean_new_symptoms(['Fever'], ['A'], existing_names=['Fever'])

    def test_builds_a_code_outside_the_trained_symptom_list(self):
        self.assertEqual(code_for_new_symptom('Swollen lymph nodes'), 'added_swollen_lymph_nodes')
