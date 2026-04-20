import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

def _load_env_file_fallback(env_path):
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

_ENV_PATH = Path(__file__).resolve().parent / '.env'
if load_dotenv:
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    _load_env_file_fallback(_ENV_PATH)


def _env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')

class Config:
    def __init__(self):
        app_root = Path(__file__).resolve().parent
        self.APP_ENV = os.environ.get('APP_ENV', 'development').strip().lower()
        self.IS_PRODUCTION = self.APP_ENV == 'production'

        self.SECRET_KEY = os.environ.get(
            'SECRET_KEY',
            'dev-only-change-me-before-production'
        )

        # PostgreSQL configuration: supports either DATABASE_URL or host/user/password fields.
        self.DB_HOST = os.environ.get('DB_HOST', 'localhost')
        self.DB_PORT = os.environ.get('DB_PORT', '5432')
        self.DB_NAME = os.environ.get('DB_NAME', 'vigilance_tracker')
        self.DB_USER = os.environ.get('DB_USER', 'postgres')
        self.DB_PASSWORD = os.environ.get('DB_PASSWORD')
        self.DB_SSLMODE = os.environ.get('DB_SSLMODE', 'prefer')
        self.DB_CONNECT_TIMEOUT = int(os.environ.get('DB_CONNECT_TIMEOUT', '10'))
        self.DB_SCHEMA = os.environ.get('DB_SCHEMA', 'public').strip() or 'public'
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', self.DB_SCHEMA):
            raise RuntimeError(
                "Invalid DB_SCHEMA value. Use a valid PostgreSQL identifier (e.g., public or vigilance_tracker)."
            )

        # App runtime configuration
        self.HOST = os.environ.get('HOST', '0.0.0.0')
        self.PORT = int(os.environ.get('PORT', '5000'))
        self.DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1' and not self.IS_PRODUCTION
        self.BRAND_NAME = os.environ.get('BRAND_NAME', 'Nigaa').strip() or 'Nigaa'
        self.BRAND_SUBTITLE = os.environ.get('BRAND_SUBTITLE', 'Petition Tracker').strip() or 'Petition Tracker'
        self.BRAND_LOGO_FILE = os.environ.get('BRAND_LOGO_FILE', 'img/nigaa-logo.svg').strip() or 'img/nigaa-logo.svg'
        self.BRAND_LOGO_FALLBACK = os.environ.get('BRAND_LOGO_FALLBACK', 'img/aptransco-logo-fallback.svg').strip() or 'img/aptransco-logo-fallback.svg'

        # Storage/session controls
        storage_path_raw = (
            os.environ.get('FILE_STORAGE_PATH')
            or os.environ.get('UPLOAD_BASE_DIR')
            or 'uploads'
        ).strip()
        storage_path = Path(storage_path_raw)
        if storage_path.is_absolute():
            resolved_storage_path = storage_path
        else:
            resolved_storage_path = (app_root / storage_path).resolve()
        self.UPLOAD_BASE_DIR = str(resolved_storage_path)
        self.MAX_UPLOAD_SIZE_MB = int(os.environ.get('MAX_UPLOAD_SIZE_MB', '10'))
        self.SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', self.IS_PRODUCTION)
        self.SESSION_COOKIE_NAME = (
            os.environ.get('SESSION_COOKIE_NAME')
            or ('__Host-nigaa_session' if self.IS_PRODUCTION and self.SESSION_COOKIE_SECURE else 'nigaa_session')
        ).strip() or 'nigaa_session'
        self.SESSION_COOKIE_DOMAIN = (os.environ.get('SESSION_COOKIE_DOMAIN') or '').strip() or None
        self.SESSION_COOKIE_PATH = (os.environ.get('SESSION_COOKIE_PATH') or '/').strip() or '/'
        session_cookie_samesite = (os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax') or 'Lax').strip().capitalize()
        if session_cookie_samesite not in {'Lax', 'Strict'}:
            raise RuntimeError("Invalid SESSION_COOKIE_SAMESITE value. Use Lax or Strict.")
        self.SESSION_COOKIE_SAMESITE = session_cookie_samesite
        self.SESSION_LIFETIME_MINUTES = int(os.environ.get('SESSION_LIFETIME_MINUTES', '120'))
        self.SESSION_INACTIVITY_MINUTES = int(
            os.environ.get('SESSION_INACTIVITY_MINUTES', str(self.SESSION_LIFETIME_MINUTES))
        )
        self.SESSION_ABSOLUTE_HOURS = int(os.environ.get('SESSION_ABSOLUTE_HOURS', '24'))
        self.SESSION_TOUCH_THRESHOLD_SECONDS = max(
            30, int(os.environ.get('SESSION_TOUCH_THRESHOLD_SECONDS', '300'))
        )
        self.MAX_CONCURRENT_SESSIONS = max(1, int(os.environ.get('MAX_CONCURRENT_SESSIONS', '3')))
        self.REVOKE_OTHER_SESSIONS_ON_LOGIN = _env_bool('REVOKE_OTHER_SESSIONS_ON_LOGIN', False)
        self.LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get('LOGIN_RATE_LIMIT_WINDOW_SECONDS', '600'))
        self.LOGIN_RATE_LIMIT_MAX_ATTEMPTS = int(os.environ.get('LOGIN_RATE_LIMIT_MAX_ATTEMPTS', '8'))
        self.LOGIN_RATE_LIMIT_BLOCK_SECONDS = int(os.environ.get('LOGIN_RATE_LIMIT_BLOCK_SECONDS', '900'))
        self.TRUST_PROXY_HEADERS = os.environ.get('TRUST_PROXY_HEADERS', '0') == '1'
        self.PROXY_FIX_X_FOR = max(0, int(os.environ.get('PROXY_FIX_X_FOR', '1')))
        self.PROXY_FIX_X_PROTO = max(0, int(os.environ.get('PROXY_FIX_X_PROTO', '1')))
        self.PROXY_FIX_X_HOST = max(0, int(os.environ.get('PROXY_FIX_X_HOST', '1')))
        self.PROXY_FIX_X_PORT = max(0, int(os.environ.get('PROXY_FIX_X_PORT', '1')))
        self.PETITION_USER_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get('PETITION_USER_RATE_LIMIT_WINDOW_SECONDS', '300'))
        self.PETITION_USER_RATE_LIMIT_MAX_SUBMISSIONS = int(os.environ.get('PETITION_USER_RATE_LIMIT_MAX_SUBMISSIONS', '10'))
        self.PETITION_USER_RATE_LIMIT_BLOCK_SECONDS = int(os.environ.get('PETITION_USER_RATE_LIMIT_BLOCK_SECONDS', '300'))
        self.PETITION_IP_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get('PETITION_IP_RATE_LIMIT_WINDOW_SECONDS', '300'))
        self.PETITION_IP_RATE_LIMIT_MAX_SUBMISSIONS = int(os.environ.get('PETITION_IP_RATE_LIMIT_MAX_SUBMISSIONS', '60'))
        self.PETITION_IP_RATE_LIMIT_BLOCK_SECONDS = int(os.environ.get('PETITION_IP_RATE_LIMIT_BLOCK_SECONDS', '180'))

        # HTTPS redirect — redirect plain-HTTP requests to HTTPS at the app level.
        # Enable in production when not handled by a reverse proxy already.
        self.FORCE_HTTPS = _env_bool('FORCE_HTTPS', self.IS_PRODUCTION)

        # Logging — structured JSON logs written to a rotating file.
        self.LOG_FILE = (os.environ.get('LOG_FILE') or '').strip() or None
        self.LOG_LEVEL = (os.environ.get('LOG_LEVEL') or 'INFO').strip().upper()
        self.LOG_MAX_BYTES = max(1024 * 1024, int(os.environ.get('LOG_MAX_BYTES', str(10 * 1024 * 1024))))
        self.LOG_BACKUP_COUNT = max(1, int(os.environ.get('LOG_BACKUP_COUNT', '5')))

        if self.IS_PRODUCTION:
            self._validate_production_settings()
        self._validate_session_cookie_settings()

    def _validate_session_cookie_settings(self):
        if not self.SESSION_COOKIE_PATH.startswith('/'):
            raise RuntimeError("SESSION_COOKIE_PATH must start with '/'.")
        if self.SESSION_COOKIE_NAME.startswith('__Host-'):
            if not self.SESSION_COOKIE_SECURE:
                raise RuntimeError("__Host- cookies require SESSION_COOKIE_SECURE=1.")
            if self.SESSION_COOKIE_DOMAIN:
                raise RuntimeError("__Host- cookies must not set SESSION_COOKIE_DOMAIN.")
            if self.SESSION_COOKIE_PATH != '/':
                raise RuntimeError("__Host- cookies require SESSION_COOKIE_PATH=/.")

    def _validate_production_settings(self):
        missing = []
        database_url = os.environ.get('DATABASE_URL')

        if not self.SECRET_KEY or self.SECRET_KEY == 'dev-only-change-me-before-production':
            missing.append('SECRET_KEY')

        if not database_url:
            required_db = {
                'DB_HOST': self.DB_HOST,
                'DB_PORT': self.DB_PORT,
                'DB_NAME': self.DB_NAME,
                'DB_USER': self.DB_USER,
                'DB_PASSWORD': self.DB_PASSWORD,
            }
            for key, value in required_db.items():
                if not value:
                    missing.append(key)

        if missing:
            raise RuntimeError(
                "Missing required production environment variables: "
                + ", ".join(missing)
            )

        # Prevent unencrypted DB connections in production for remote hosts.
        # Loopback addresses (localhost / 127.x / ::1) are exempt because local
        # PostgreSQL instances typically don't have SSL configured.
        _loopback = {'localhost', '127.0.0.1', '::1', ''}
        db_host = (os.environ.get('DATABASE_URL') or self.DB_HOST or '').strip()
        is_loopback = any(db_host == h or db_host.startswith('127.') for h in _loopback)
        if not is_loopback and self.DB_SSLMODE not in ('require', 'verify-ca', 'verify-full'):
            raise RuntimeError(
                "Production requires DB_SSLMODE=require (or verify-ca/verify-full) "
                f"for remote host '{db_host}'. Current value: '{self.DB_SSLMODE}'. "
                "Set DB_SSLMODE=require in .env to enforce TLS to PostgreSQL."
            )

    @property
    def DATABASE_URL(self):
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return database_url

        password_part = self.DB_PASSWORD or ''
        return (
            f"postgresql://{self.DB_USER}:{password_part}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    def get_psycopg2_kwargs(self):
        database_url = os.environ.get('DATABASE_URL')
        search_path_option = f"-c search_path={self.DB_SCHEMA},public"
        if database_url:
            return {
                'dsn': database_url,
                'connect_timeout': self.DB_CONNECT_TIMEOUT,
                'options': search_path_option,
            }

        kwargs = {
            'host': self.DB_HOST,
            'port': self.DB_PORT,
            'dbname': self.DB_NAME,
            'user': self.DB_USER,
            'connect_timeout': self.DB_CONNECT_TIMEOUT,
            'sslmode': self.DB_SSLMODE,
            'options': search_path_option,
        }
        if self.DB_PASSWORD is not None:
            kwargs['password'] = self.DB_PASSWORD
        return kwargs
