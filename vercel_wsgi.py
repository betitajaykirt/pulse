import os
import pymysql

# 1. Force PyMySQL to act as the database driver right away
pymysql.install_as_MySQLdb()

# 2. Tell Django exactly where your settings file is BEFORE importing anything else
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# 3. Now import the WSGI application safely
from mysite.wsgi import application
app = application