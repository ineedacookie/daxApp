"""
Django settings for daxApp project.
"""

import os
import datetime
import boto3
from django.contrib.messages import constants as messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-ur1z-(2dw^fbsewe+h7ygpv%xz2$!dk366f)eqzw$lyaw*qx#4'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

DOMAIN = '127.0.0.1:8000'

# Application definition

INSTALLED_APPS = [
    'channels',
    'channels.layers',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'users',  # Custom Users dg 4/9/20
    'feedback', # Feedback Module dg 5/19/20
    'admin_auto_filters',   # additional admin functionality django admin dg 5/12/2020
    'log_viewer',   # additional admin functionality for viewing a log file dg 5/13/2020
    'time_tracker',     # A time tracking app dg 10/22/2022
]   # by default, it always fails silently. Makes things easier to debug like this

MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'middleware.timezone.TimezoneMiddleware',
]

ROOT_URLCONF = 'daxApp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'daxApp.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',  # TODO replace with something more robust
    },
}

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'static') #TODO switch back to staticfiles when deploying.

STATIC_URL = 'static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

AUTH_USER_MODEL = 'users.CustomUser'  # Added by Dax 4/9/2020

S3_ACCESS_KEY = 'AKIARTGAAP52Y4CTGFYS'
S3_SECRET = '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'
S3_CLIENT = boto3.client(
    's3',
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET
)
S3_BUCKET_NAME = 'daxapp'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'  # Added by Dax to redirect a user to the home page once logged in 4/10/20

# TODO update this when in production
DEFAULT_FROM_EMAIL = 'graydax@gmail.com'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'graydax@gmail.com'
EMAIL_HOST_PASSWORD = 'folqufzxkokcfydg'
EMAIL_USE_TLS = True

PASSWORD_RESET_TIMEOUT_DAYS = 7

NOW = datetime.datetime.now()
DAY_NAME = NOW.strftime('%A').lower()

MAXIMUM_FILE_LOGS = 1024 * 1024 * 10  # 10 MB
BACKUP_COUNT = 5


# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'standard': {
#             'format': '[%(levelname)s] %(asctime)s %(name)s: %(message)s'
#         },
#     },
#     'handlers': {
#         'default': {
#             'level': 'DEBUG',
#             'class': 'logging.handlers.RotatingFileHandler',
#             'filename': 'logs/default.log',
#             'maxBytes': MAXIMUM_FILE_LOGS,
#             'backupCount': BACKUP_COUNT,
#             'formatter': 'standard',
#         },
#         'request_nicepay_handler': {
#             'level': 'DEBUG',
#             'class': 'logging.handlers.RotatingFileHandler',
#             'filename': 'logs/nicepay/%s.log' % DAY_NAME,
#             'maxBytes': MAXIMUM_FILE_LOGS,
#             'backupCount': BACKUP_COUNT,
#             'formatter': 'standard',
#         },
#         'request_debug_handler': {
#             'level': 'DEBUG',
#             'class': 'logging.handlers.RotatingFileHandler',
#             'filename': 'logs/request_debug.log',
#             'maxBytes': MAXIMUM_FILE_LOGS,
#             'backupCount': BACKUP_COUNT,
#             'formatter': 'standard',
#         },
#         'request_error_handler': {
#             'level': 'ERROR',
#             'class': 'logging.handlers.RotatingFileHandler',
#             'filename': 'logs/request_error.log',
#             'maxBytes': MAXIMUM_FILE_LOGS,
#             'backupCount': BACKUP_COUNT,
#             'formatter': 'standard',
#         },
#         'mail_admins_handler': {
#             'level': 'ERROR',
#             'class': 'django.utils.log.AdminEmailHandler',
#             'email_backend': 'django.core.mail.backends.smtp.EmailBackend'
#         },
#     },
#     'root': {
#         'handlers': ['default', 'request_nicepay_handler'],
#         'level': 'DEBUG'
#     },
#     'loggers': {
#         'django.request': {
#             'handlers': [
#                 'request_nicepay_handler',
#                 'request_debug_handler',
#                 'request_error_handler',
#                 'mail_admins_handler'
#             ],
#             'level': 'DEBUG',
#             'propagate': False
#         },
#     }
# }
#
# LOG_VIEWER_FILES_DIR = os.path.join(BASE_DIR, 'logs')
# LOG_VIEWER_MAX_READ_LINES = 1000  # total log lines will be read
# LOG_VIEWER_PAGE_LENGTH = 25       # total log lines per-page
#
# # Optionally you can set the next variables in order to customize the admin:
#
# LOG_VIEWER_FILE_LIST_TITLE = "Logs"
# LOG_VIEWER_FILE_LIST_STYLES = None
#
# MESSAGE_TAGS = {
#     messages.DEBUG: 'alert-info',
#     messages.INFO: 'alert-info',
#     messages.SUCCESS: 'alert-success',
#     messages.WARNING: 'alert-warning',
#     messages.ERROR: 'alert-danger',
# }


# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ENCRYPT_CODE = b"The Craziest pass3wrd you321 have enver seen"
