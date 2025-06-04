import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Caminho base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Carrega variáveis do .env antes de qualquer uso de os.getenv
load_dotenv(BASE_DIR / '.env')
# No início do settings.py, após load_dotenv

# Chave secreta e modo de depuração
SECRET_KEY = os.getenv('SECRET_KEY', 'chave-insegura-para-dev')
DEBUG = os.getenv('DEBUG', 'False') == 'True'


cloudinary.config(
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key = os.getenv('CLOUDINARY_API_KEY'),
    api_secret = os.getenv('CLOUDINARY_API_SECRET'),
    secure = True
)


# Hosts permitidos
ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'www.lanchonetedeliciadecoxinha.kesug.com',
    'lanchonetedeliciadecoxinha.kesug.com'
]

# Configurações específicas para Render
if 'RENDER' in os.environ:
    RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if RENDER_EXTERNAL_HOSTNAME:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Ajustes para segurança em produção
if DEBUG:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False

# Aplicativos instalados
INSTALLED_APPS = [
    'corsheaders',
    'crispy_bootstrap5',
    'crispy_forms',
    'import_export',
    'cardapio',
    # app Cloudinary para models
    'cloudinary_storage',
    'cloudinary',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# Middlewares
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Adiciona o middleware de Whitenoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cardapio.middleware.CarrinhoMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    "https://www.mercadopago.com.br",
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

# Banco de dados
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# Validações de senha
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Configurações de data/hora
TIME_ZONE = 'America/Sao_Paulo'
USE_TZ = True

# Configurações de formulários
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Redirecionamentos de login/logout
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/menu/'

# Configurações de import/export
IMPORT_EXPORT_USE_TRANSACTIONS = True
IMPORT_EXPORT_SKIP_ADMIN_LOG = False

# Configurações do Mercado Pago
MERCADOPAGO = {
    'ACCESS_TOKEN': os.getenv('MERCADOPAGO_ACCESS_TOKEN'),
    'PUBLIC_KEY': os.getenv('MERCADOPAGO_PUBLIC_KEY'),
    'SANDBOX_MODE': os.getenv('SANDBOX_MODE', 'False') == 'True',
    'AUTO_RETURN': 'approved',
    'WEBHOOK_URL': os.getenv('WEBHOOK_URL'),
    'NOTIFICATION_URL': os.getenv('NOTIFICATION_URL')
}

# Confiança para requisições externas (webhook)
CSRF_TRUSTED_ORIGINS = [
    'https://api.mercadopago.com',
    'https://www.mercadopago.com.br'
]

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MEDIA_URL = f"https://res.cloudinary.com/{os.getenv('CLOUDINARY_CLOUD_NAME')}/image/upload/"
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Whitenoise para static
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MERCADOPAGO_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET")





