import os
from mysite.wsgi import application

# Point Django settings explicitly for the Vercel server environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

app = application