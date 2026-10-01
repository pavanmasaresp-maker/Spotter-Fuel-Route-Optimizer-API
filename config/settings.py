import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DEBUG", "1") == "1"
# ".app.github.dev" lets the forwarded GitHub Codespaces URL work.
ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    "ALLOWED_HOSTS", "127.0.0.1,localhost,.app.github.dev").split(",") if h.strip()]

INSTALLED_APPS = ["routing"]
MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = []
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
GEOCODER_USER_AGENT = os.getenv("GEOCODER_USER_AGENT", "spotter-fuel-route-assessment/1.0")
ROUTE_CACHE_TTL = int(os.getenv("ROUTE_CACHE_TTL", "3600"))
GEOCODE_CACHE_TTL = int(os.getenv("GEOCODE_CACHE_TTL", "86400"))
MAX_RANGE_MILES = float(os.getenv("MAX_RANGE_MILES", "500"))
MPG = float(os.getenv("MPG", "10"))
STATION_CORRIDOR_MILES = float(os.getenv("STATION_CORRIDOR_MILES", "30"))
