import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Segurança e Debug
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Aplicações instaladas
INSTALLED_APPS = [
    'crispy_bootstrap5',
    'crispy_forms',
    'import_export',
    'cardapio',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# Middlewares
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cardapio.middleware.CarrinhoMiddleware',
]

ROOT_URLCONF = 'lanchonete.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'lanchonete.wsgi.application'

# Modelo de usuário customizado
AUTH_USER_MODEL = 'cardapio.Usuario'

# Banco de dados - SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Validação de senha
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internacionalização
TIME_ZONE = 'America/Sao_Paulo'
USE_TZ = True

# Arquivos estáticos
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / os.getenv('STATIC_ROOT', 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Campo padrão
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django-crispy-forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Login/Logout
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/menu/'

# Import Export
IMPORT_EXPORT_USE_TRANSACTIONS = True
IMPORT_EXPORT_SKIP_ADMIN_LOG = False

# Mercado Pago via variáveis de ambiente
MERCADOPAGO = {
    'ACCESS_TOKEN': os.getenv('MERCADOPAGO_ACCESS_TOKEN'),
    'PUBLIC_KEY': os.getenv('MERCADOPAGO_PUBLIC_KEY'),
    'SANDBOX_MODE': os.getenv('SANDBOX_MODE', 'False') == 'True',
    'AUTO_RETURN': True,
    'WEBHOOK_URL': os.getenv('WEBHOOK_URL', 'http://127.0.0.1:8000/'),
    'NOTIFICATION_URL': os.getenv('NOTIFICATION_URL', 'http://127.0.0.1:8000/')
}
