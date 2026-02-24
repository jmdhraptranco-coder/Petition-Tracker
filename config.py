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

class Config:
    def __init__(self):
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

        # Storage/session controls
        self.UPLOAD_BASE_DIR = os.environ.get(
            'UPLOAD_BASE_DIR',
            os.path.join(os.path.dirname(__file__), 'uploads')
        )
        self.MAX_UPLOAD_SIZE_MB = int(os.environ.get('MAX_UPLOAD_SIZE_MB', '10'))
        self.SESSION_COOKIE_SECURE = self.IS_PRODUCTION

        if self.IS_PRODUCTION:
            self._validate_production_settings()

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
