import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from reports.prediction_service import analyze_patient_case
from myapp.models import SurveillanceReport

print("Count before:", SurveillanceReport.objects.count())

from myapp.models import SurveillanceReport, Barangay
b, _ = Barangay.objects.get_or_create(barangay_name='Dulao', defaults={'city': 'City', 'coordinates': '', 'population': 1000})

from django.utils import timezone
now = timezone.now()
from myapp.models import User
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

print("Count after:", SurveillanceReport.objects.count())

today = now.date()
count1 = SurveillanceReport.objects.filter(barangay__barangay_name='Dulao', report_date__date=today).count()
print("Count with __date:", count1)

from datetime import datetime, time, timedelta
start = now.replace(hour=0, minute=0, second=0, microsecond=0)
end = start + timedelta(days=1)
count2 = SurveillanceReport.objects.filter(barangay__barangay_name='Dulao', report_date__gte=start, report_date__lt=end).count()
print("Count with __gte:", count2)
