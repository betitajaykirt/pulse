from datetime import date

from django.test import SimpleTestCase

from myapp.field_encryption import decrypt_text, encrypt_text, scrub_identity_from_remarks
from myapp.fields import EncryptedDateField


class FieldEncryptionTests(SimpleTestCase):
    def test_name_round_trip_hides_the_plain_value(self):
        token = encrypt_text('Maria Cruz')
        self.assertTrue(token.startswith('enc1:'))
        self.assertNotIn('Maria', token)
        self.assertEqual(decrypt_text(token), 'Maria Cruz')
        self.assertEqual(encrypt_text('Maria Cruz'), token)

    def test_date_field_reads_old_and_new_values(self):
        field = EncryptedDateField()
        stored = field.get_prep_value(date(2010, 1, 15))
        self.assertEqual(field.from_db_value(stored, None, None), date(2010, 1, 15))
        self.assertEqual(field.from_db_value(date(2010, 1, 15), None, None), date(2010, 1, 15))
        self.assertEqual(field.from_db_value('2010-01-15', None, None), date(2010, 1, 15))

    def test_remarks_keep_the_prediction_and_drop_the_name(self):
        text = 'Patient: Maria Cruz | Age: 8 | Address: Purok 1 | ML Top Prediction: Dengue Fever'
        self.assertEqual(
            scrub_identity_from_remarks(text),
            'Age: 8 | Address: Purok 1 | ML Top Prediction: Dengue Fever',
        )
