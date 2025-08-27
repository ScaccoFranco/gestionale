from .base import *

# Development settings
DEBUG = True

# Add testserver for Django test client
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']

# Use SQLite for local development to avoid database setup issues
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Use local cache for development instead of Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Use database sessions instead of cache for development
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Security - disable in development
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Add debug toolbar if available
try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware')
except ImportError:
    pass

# Add django_extensions if available
try:
    import django_extensions
    INSTALLED_APPS += ['django_extensions']
except ImportError:
    pass

# Add django_filters if available
try:
    import django_filters
    INSTALLED_APPS += ['django_filters']
except ImportError:
    pass

# Internal IPs for debug toolbar
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Allow all CORS origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Less strict session cookies
SESSION_COOKIE_SECURE = False

# Development-specific logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}