from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from django.conf import settings


# ──────────────────────────────────────────────
# Утилиты для работы с паролями (bcrypt)
# ──────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Хэшируем пароль через bcrypt. Возвращаем строку для сохранения в БД."""
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Проверяем, соответствует ли открытый пароль сохранённому хэшу."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


# ──────────────────────────────────────────────
# Утилиты для работы с JWT
# ──────────────────────────────────────────────

def generate_token(user_id: int, role_id: Optional[int] = None) -> str:
    """
    Генерируем JWT-токен с полезной нагрузкой:
      - sub      : идентификатор пользователя (строка — требование PyJWT 2.x)
      - role_id  : идентификатор роли (для быстрой проверки прав)
      - iat      : время выдачи
      - exp      : время истечения (берём из settings.JWT_EXPIRATION_HOURS)
    """
    expiration_hours: int = getattr(settings, "JWT_EXPIRATION_HOURS", 24)

    payload = {
        "sub": str(user_id),  # PyJWT 2.x
        "role_id": role_id,
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=expiration_hours),
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token


def decode_token(token: str) -> dict:
    """
    Декодируем и верифицируем JWT-токен.

    Возможные исключения (перехватываются в middleware):
      - jwt.ExpiredSignatureError  — токен просрочен
      - jwt.InvalidTokenError      — токен невалиден
    """
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    # PyJWT 2.x хранит sub как строку — конвертируем в int для ORM-запросов.
    if "sub" in payload:
        payload["sub"] = int(payload["sub"])
    return payload