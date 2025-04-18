import os
import sys
from pathlib import Path
from urllib import request
from django.http.request import validate_host
from dotenv import load_dotenv
print("MERCADOPAGO_ACCESS_TOKEN:", os.getenv('MERCADOPAGO_ACCESS_TOKEN'))

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Carrega variáveis de ambiente do .env
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'chave-insegura-para-dev')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# settings.py

# Defina DEBUG como True para desenvolvimento
DEBUG = True

# Adicione todos os hosts necessários
ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'www.lanchonetedeliciadecoxinha.kesug.com',
    'lanchonetedeliciadecoxinha.kesug.com'
]

# Desative estas configurações de segurança para desenvolvimento
if DEBUG:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
# Adicione isto se usar Render:
if 'RENDER' in os.environ:
    RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if RENDER_EXTERNAL_HOSTNAME:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)



INSTALLED_APPS = [
    'corsheaders',
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
    'corsheaders.middleware.CorsMiddleware',
]
CORS_ALLOWED_ORIGINS = [
    "https://www.mercadopago.com.br",  # URL do Mercado Pago
]
ROOT_URLCONF = 'lanchonete.urls'

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
AUTH_USER_MODEL = 'cardapio.Usuario'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

TIME_ZONE = 'America/Sao_Paulo'
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/menu/'

IMPORT_EXPORT_USE_TRANSACTIONS = True
IMPORT_EXPORT_SKIP_ADMIN_LOG = False

MERCADOPAGO = {
    'ACCESS_TOKEN': os.getenv('MERCADOPAGO_ACCESS_TOKEN'),
    'PUBLIC_KEY': os.getenv('MERCADOPAGO_PUBLIC_KEY'),
    'SANDBOX_MODE': os.getenv('SANDBOX_MODE', 'False') == 'True',
    'AUTO_RETURN': 'approved',
    'WEBHOOK_URL': os.getenv('WEBHOOK_URL'),
    'NOTIFICATION_URL': os.getenv('NOTIFICATION_URL')

}
# Configurações de segurança para o webhook
CSRF_TRUSTED_ORIGINS = [
    'https://api.mercadopago.com',
    'https://www.mercadopago.com.br'
]