"""
WSGI config for lanchonete project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lanchonete.settings')

application = get_wsgi_application()


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SiteCoxinha.settings')

application = get_wsgi_application()
application = WhiteNoise(application)