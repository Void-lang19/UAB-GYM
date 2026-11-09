import os

from flask_appbuilder.security.manager import AUTH_DB
from sqlalchemy.engine import URL


_EXAMPLE_SECRET = "replace-me-with-a-random-secret"


def load_config() -> dict[str, object]:
    secret_key = os.getenv("SECRET_KEY", "").strip()
    if len(secret_key) < 32 or secret_key == _EXAMPLE_SECRET:
        raise RuntimeError(
            "SECRET_KEY debe tener al menos 32 caracteres. "
            "Genera una clave con: python -c "
            "\"import secrets; print(secrets.token_hex(32))\""
        )

    database_user = os.getenv("DB_USER", "").strip()
    database_name = os.getenv("DB_NAME", "").strip()
    if not database_user:
        raise RuntimeError("DB_USER es obligatorio en el archivo .env.")
    if not database_name:
        raise RuntimeError("DB_NAME es obligatorio en el archivo .env.")

    try:
        database_port = int(os.getenv("DB_PORT", "3306"))
    except ValueError as exc:
        raise RuntimeError("DB_PORT debe ser un número entero.") from exc

    database_url = URL.create(
        drivername="mysql+pymysql",
        username=database_user,
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=database_port,
        database=database_name,
        query={"charset": "utf8mb4"},
    )

    return {
        "APP_NAME": "UAB GYM",
        "APP_THEME": "",
        "BABEL_DEFAULT_LOCALE": "es",
        "BABEL_DEFAULT_TIMEZONE": "America/La_Paz",
        "LANGUAGES": {"es": {"flag": "es", "name": "Español (Latinoamérica)"}},
        "BABEL_TRANSLATION_DIRECTORIES": os.path.join(
            os.path.dirname(__file__), "app", "translations",
        ),
        "SECRET_KEY": secret_key,
        "SQLALCHEMY_DATABASE_URI": database_url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "AUTH_TYPE": AUTH_DB,
        "AUTH_ROLE_ADMIN": "Admin",
        "AUTH_USER_REGISTRATION": False,
        "AUTH_ROLES_SYNC_AT_LOGIN": False,
        "WTF_CSRF_ENABLED": True,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
    }
