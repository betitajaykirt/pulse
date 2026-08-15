import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from reports.prediction_service import analyze_patient_case
from myapp.models import SurveillanceReport, Barangay, User

# Clear past mock data
SurveillanceReport.objects.filter(syndrome_type='Test').delete()

print("Testing analyze_patient_case (Normal Day - 1 case)...")
result_normal = analyze_patient_case(
    age=25,
    sex='male',
    symptoms=['fever', 'headache'],
    barangay_name='Dulao'
)
print("Normal score:", result_normal['anomaly_score'])
print("Is Anomaly:", result_normal['is_anomaly'])

print("\nSimulating surge in DB (15 cases)...")
b, _ = Barangay.objects.get_or_create(barangay_name='Dulao', defaults={'city': 'City', 'coordinates': '', 'population': 1000})

from django.utils import timezone
now = timezone.now()
u, _ = User.objects.get_or_create(username='tester', defaults={'first_name': 'T', 'last_name': 'T', 'email': 't@t.com', 'password_hash': 'p', 'role': 'encoder', 'created_at': now, 'updated_at': now})

for i in range(15):
    SurveillanceReport.objects.create(
        barangay=b,
        report_date=now,
        created_at=now,
        updated_at=now,
        submitted_by=u,
        syndrome_type='Test',
    )


print("\nTesting analyze_patient_case (Surge Day - 16 cases)...")
result_surge = analyze_patient_case(
    age=25,
    sex='male',
    symptoms=['fever', 'headache'],
    barangay_name='Dulao'
)
print("Surge score:", result_surge['anomaly_score'])
print("Is Anomaly:", result_surge['is_anomaly'])

# clean up
SurveillanceReport.objects.filter(syndrome_type='Test').delete()

