from typing import Callable

import jwt
from django.http import HttpRequest

from apps.users.models import User
from apps.users.services import decode_token


class JWTAuthMiddleware:
    """
    Middleware для аутентификации по JWT.

    Извлекает токен из заголовка Authorization: Bearer <token>,
    декодирует его и прикрепляет объект пользователя к request.my_user.

    Если токен отсутствует или невалиден — request.my_user = None.
    401 возвращается только там, где требуется аутентификация
    (в классах permissions.py), а не здесь глобально.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        request.my_user = None  # По умолчанию пользователь не определён.

        auth_header: str = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            request.my_user = self._resolve_user(token, request)

        response = self.get_response(request)
        return response

    @staticmethod
    def _resolve_user(token: str, request: HttpRequest) -> "User | None":
        """
        Декодируем токен и загружаем пользователя из БД.
        Если токен просрочен или пользователь деактивирован — возвращаем None.
        """
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            # Токен истёк; проставляем флаг для формирования нужного сообщения.
            request._jwt_expired = True
            return None
        except jwt.InvalidTokenError:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        try:
            user = User.objects.select_related("role").get(pk=user_id, is_active=True)
            return user
        except User.DoesNotExist:
            return None
