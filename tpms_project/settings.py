import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps directory to sys.path so apps can be imported cleanly
sys.path.insert(0, str(BASE_DIR / 'apps'))

# Load variables from a local .env file if python-dotenv is installed.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-local-development-key-change-me-before-deploying',
)

DEBUG = env_bool('DEBUG', True)

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h.strip()]

# Demo mode shows the one-click role switcher on the login page and sidebar.
# It lets anyone sign in as any role, so it must be off on a real deployment.
DEMO_MODE = env_bool('DEMO_MODE', DEBUG)

# Institution details shown across the interface.
INSTITUTE_NAME = os.environ.get('TPMS_INSTITUTE_NAME', 'Apex Institute of Technology')
INSTITUTE_SHORT_NAME = os.environ.get('TPMS_INSTITUTE_SHORT_NAME', 'AIT')
CURRENT_ACADEMIC_YEAR = os.environ.get('TPMS_CURRENT_ACADEMIC_YEAR', '2025-26')

# AI career assistant (optional). Without a key it falls back to built-in guidance.
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-flash-latest')

# Application definition
INSTALLED_APPS = [
    # Core Django apps (Strictly NO django.contrib.admin)
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # TPMS Modular Applications
    'apps.accounts',
    'apps.core',
    'apps.departments',
    'apps.students',
    'apps.companies',
    'apps.placements',
    'apps.applications',
    'apps.study_materials',
    'apps.notifications',
    'apps.analytics',
    'apps.audit',
    'apps.career_assistant',
]

AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tpms_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.tpms_global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'tpms_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (Uploaded Resumes, Study Materials, Logos)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Session & Security Settings
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:role_redirect'
LOGOUT_REDIRECT_URL = 'core:landing'

SESSION_COOKIE_AGE = 86400  # 24 hours in seconds
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Upload limits (resumes, study materials, bulk import files)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

MESSAGE_TAGS = {40: 'danger'}

if not DEBUG:
    SESSION_COOKIE_SECURE = env_bool('SECURE_COOKIES', True)
    CSRF_COOKIE_SECURE = env_bool('SECURE_COOKIES', True)
