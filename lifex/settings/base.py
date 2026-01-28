import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv


# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR should point to the project root (LifeXBackend/), not lifex/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / '.env')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-7d1+(a^&s_2it&vitrmd+)#5mmi2=krkdnn24z-*u=c%ns31j)')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# CORS Configuration
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
CORS_ALLOW_CREDENTIALS = True


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'drf_spectacular',
    # 'django_ratelimit',  # Requires Redis - enable in production
    
    # Local apps
    'users',
    'blockchain',
    'products',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lifex.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # No custom templates for API-only backend
        'APP_DIRS': True,  # Keep for Django admin
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

WSGI_APPLICATION = 'lifex.wsgi.application'


# Database Configuration
# PostgreSQL is REQUIRED - SQLite is not supported
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME', 'LifeX'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 0,  # 0 for development, 600 for production
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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


# Cache Configuration
# For development: using dummy cache (rate limiting disabled)
# For production: use Redis or Memcached for rate limiting support
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# To enable Redis cache (recommended for production):
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     }
# }

# Cache timeout settings (in seconds)
CACHE_TTL = {
    'SYSTEM_STATS': 300,  # 5 minutes
    'USER_STATS': 180,    # 3 minutes
    'DASHBOARD': 120,     # 2 minutes
}

# Rate Limiting Configuration
RATELIMIT_ENABLE = os.getenv('RATELIMIT_ENABLE', 'False').lower() == 'true'
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Blockchain Config
BLOCKCHAIN_CONFIG = {
    'GANACHE_URL': os.getenv('GANACHE_URL', 'http://127.0.0.1:7545'),
    'CONTRACT_ADDRESS': os.getenv('CONTRACT_ADDRESS'),
    'CHAIN_ID': int(os.getenv('CHAIN_ID', '1337')),
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# STATICFILES_DIRS removed - not needed for API-only backend (admin uses STATIC_ROOT)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'LifeX Healthcare Management API',
    'DESCRIPTION': '''
    A comprehensive healthcare management system API with role-based access control.
    
    **Features:**
    - JWT Authentication with role-based permissions
    - User management (Admin, Receptionist, Nurse, Doctor, Patient)
    - Department and staff management
    - Doctor scheduling system
    - Appointment booking and management
    - Real-time notifications
    - Blockchain integration for secure medical records
    
    **Roles:**
    - **ADMIN**: Full system access
    - **RECEPTIONIST**: Patient check-in, appointment booking
    - **NURSE**: Patient care, appointment assistance
    - **DOCTOR**: Patient consultations, medical records
    - **PATIENT**: View appointments, update profile
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication and authorization'},
        {'name': 'User Management', 'description': 'User profile and account management'},
        {'name': 'Hospital Structure', 'description': 'Departments and staff organization'},
        {'name': 'Scheduling', 'description': 'Doctor schedules and availability'},
        {'name': 'Appointments', 'description': 'Appointment booking and management'},
        {'name': 'Notifications', 'description': 'System notifications and alerts'},
        {'name': 'Blockchain', 'description': 'Blockchain integration for medical records'},
    ],
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================================
# BIOMETRIC AUTHENTICATION SETTINGS
# ============================================================================

BIOMETRIC_SETTINGS = {
    # Face Recognition
    'FACE_MATCH_THRESHOLD': 0.75,  # 0-1, lower = stricter (for 1:1 matching with email) - Lenient for low quality mobile cameras
    'FACE_MATCH_THRESHOLD_1N': 0.65,  # Stricter threshold for 1:N matching (face-only login) - Balanced
    'MIN_FACE_SIZE': (100, 100),  # Minimum face size in pixels
    'MAX_FACE_SIZE': (2000, 2000),  # Maximum face size in pixels
    
    # Image Quality Requirements
    'MIN_IMAGE_SIZE': (640, 480),  # Minimum image resolution (width, height)
    'MAX_IMAGE_SIZE': 10 * 1024 * 1024,  # Maximum file size: 10MB
    'MIN_SHARPNESS': 30,  # Minimum Laplacian variance (blur detection) - Lenient for mobile cameras
    'MIN_BRIGHTNESS': 50,  # Minimum average brightness (0-255)
    'MAX_BRIGHTNESS': 200,  # Maximum average brightness (0-255)
    'ALLOWED_IMAGE_FORMATS': ['JPEG', 'PNG', 'JPG'],  # Allowed image formats
    
    # Liveness Detection
    'LIVENESS_ENABLED': True,  # Enable liveness detection
    'LIVENESS_THRESHOLD': 0.7,  # Confidence threshold for liveness (0-1)
    'BLINK_EAR_THRESHOLD': 0.25,  # Eye Aspect Ratio for blink detection
    'MOVEMENT_THRESHOLD': 20,  # Minimum head movement in pixels
    'TEXTURE_THRESHOLD': 0.5,  # Texture analysis threshold for print attack detection
    'MIN_VIDEO_FRAMES': 30,  # Minimum frames for video-based liveness
    'MAX_VIDEO_DURATION': 10,  # Maximum video duration in seconds
    
    # Rate Limiting (Security)
    'MAX_ATTEMPTS_PER_MINUTE': 5,  # Maximum face login attempts per minute per IP
    'MAX_ATTEMPTS_PER_HOUR': 10,  # Maximum face login attempts per hour per user
    'LOCKOUT_DURATION': 3600,  # Lockout duration in seconds (1 hour)
    'MAX_FAILED_ATTEMPTS_BEFORE_LOCKOUT': 5,  # Failed attempts before account lockout
    
    # Session Management
    'SESSION_TOKEN_EXPIRY': 60,  # Session token expiry in seconds (for 2-step face login)
    'MAX_AMBIGUOUS_MATCHES': 3,  # Maximum ambiguous matches to return in 1:N matching
    'AMBIGUOUS_MATCH_THRESHOLD': 0.65,  # Threshold for considering a match ambiguous
    
    # Blockchain Integration
    'BLOCKCHAIN_ENABLED': True,  # Enable blockchain verification
    'AUTO_VERIFY_BLOCKCHAIN': True,  # Automatically verify on blockchain after registration
    'BLOCKCHAIN_TIMEOUT': 30,  # Blockchain operation timeout in seconds
    
    # OCR Settings
    'OCR_CONFIDENCE_THRESHOLD': 60,  # Minimum OCR confidence percentage
    'OCR_MAX_RETRIES': 3,  # Maximum OCR retry attempts
    'SUPPORTED_ID_TYPES': ['NATIONAL_ID', 'DRIVERS_LICENSE', 'PHILHEALTH_ID'],
    
    # Face Encoding Storage
    'ENCRYPT_FACE_ENCODINGS': False,  # Enable encryption of face encodings (requires BIOMETRIC_ENCRYPTION_KEY)
    'ENCODING_DIMENSION': 128,  # Face encoding dimension (face_recognition uses 128)
}

# Tesseract OCR Configuration
TESSERACT_CMD = os.environ.get('TESSERACT_CMD', 'tesseract')
TESSERACT_LANG = 'eng'  # Language for OCR (English for Philippine IDs)

# Face Recognition Models
FACE_LANDMARK_MODEL = BASE_DIR / 'media' / 'models' / 'shape_predictor_68_face_landmarks.dat'

# Biometric Encryption (for encrypting face encodings at rest)
BIOMETRIC_ENCRYPTION_KEY = os.environ.get('BIOMETRIC_ENCRYPTION_KEY', '')

# Redis Configuration (for caching and rate limiting)
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
