import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================================
# 1. CRITICAL SECURITY SETTINGS
# ==========================================

# SAFEGUARD: Force DEBUG to False by default. Only enable if explicitly set to "True".
DEBUG = os.getenv("DEBUG", "False") == "True"

# SAFEGUARD: Never use a fallback key in production. Crash immediately if missing.
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY and not DEBUG:
    raise ImproperlyConfigured("CRITICAL: DJANGO_SECRET_KEY environment variable is missing in production!")
elif not SECRET_KEY:
    SECRET_KEY = "django-insecure-dev-key-only"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ==========================================
# 2. APPLICATION DEFINITION
# ==========================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    # Internal apps
    "accounts",       
    "tokens",         
    "payments",       
    "tracking",       
    "snapsearch",     
    "admin_panel",    
    "geminiSearch",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    
    # 🚨 RESTORED: Critical for protecting Django Admin and session views
    "django.middleware.csrf.CsrfViewMiddleware", 
    
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = "core.wsgi.application"

# ==========================================
# 3. DATABASE
# ==========================================
# Note: Consider switching to dj-database-url and PostgreSQL in production
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME":   BASE_DIR / "db.sqlite3",
    }
}

# ==========================================
# 4. CORS & HEADERS
# ==========================================

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
CORS_ALLOW_CREDENTIALS = True

# ==========================================
# 5. REST FRAMEWORK (CLERK JWT)
# ==========================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["accounts.authentication.ClerkJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES":     ["rest_framework.permissions.IsAuthenticated"],
}

# ==========================================
# 6. PRODUCTION SECURITY HEADERS (NEW)
# ==========================================

if not DEBUG:
    # Forces all traffic to HTTPS
    SECURE_SSL_REDIRECT = True
    
    # Prevents browser from guessing content types (mitigates XSS)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    
    # Enables XSS filter in browsers
    SECURE_BROWSER_XSS_FILTER = True
    
    # Ensures cookies are only sent over HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # HTTP Strict Transport Security (HSTS) - Forces browsers to ONLY use HTTPS for 1 year
    SECURE_HSTS_SECONDS = 31536000  
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ==========================================
# 7. I18N & STATIC FILES
# ==========================================
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "Africa/Lagos"
USE_I18N = True
USE_TZ   = True

STATIC_URL  = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==========================================
# 8. EXTERNAL API KEYS
# ==========================================
CLERK_JWKS_URL        = os.getenv("CLERK_JWKS_URL", "https://api.clerk.com/v1/jwks")
ANTHROPIC_API_KEY     = os.getenv("ANTHROPIC_API_KEY")
PAYSTACK_SECRET_KEY   = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY   = os.getenv("PAYSTACK_PUBLIC_KEY")
AMAZON_ACCESS_KEY     = os.getenv("AMAZON_ACCESS_KEY")
AMAZON_SECRET_KEY     = os.getenv("AMAZON_SECRET_KEY")
AMAZON_ASSOCIATE_TAG  = os.getenv("AMAZON_ASSOCIATE_TAG")
ALIEXPRESS_APP_KEY    = os.getenv("ALIEXPRESS_APP_KEY")
ALIEXPRESS_APP_SECRET = os.getenv("ALIEXPRESS_APP_SECRET")
EBAY_APP_ID           = os.getenv("EBAY_APP_ID")
EBAY_CAMPAIGN_ID      = os.getenv("EBAY_CAMPAIGN_ID")
GEMINI_API_KEY        = os.getenv("GEMINI_API_KEY")
PREFERRED_AI_PROVIDER = os.getenv("PREFERRED_AI_PROVIDER", "gemini")



GVS_CREDENTIALS = {
    "type": os.getenv("SCP_TYPE", "service_account"),
    "project_id": os.getenv("SCP_PROJECT_ID"),
    "private_key_id": os.getenv("SCP_PRIVATE_KEY_ID"),
    # Replace literal \n with real newlines — .env files flatten them
    "private_key": os.getenv("SCP_PRIVATE_KEY", "").replace("\\n", "\n"),
    "client_email": os.getenv("SCP_CLIENT_EMAIL"),
    "client_id": os.getenv("SCP_CLIENT_ID"),
    "token_uri": os.getenv("SCP_TOKEN_URI", "https://oauth2.googleapis.com/token"),
}