"""
WSGI config for FinanceOS IA project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financeos.settings')

application = get_wsgi_application()
