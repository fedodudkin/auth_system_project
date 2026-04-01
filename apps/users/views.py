from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users import services
from apps.users.models import User
from apps.users.serializers import (
    UserLoginSerializer,
    UserRegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


@method_decorator(
    # 3 регистрации с одного IP за 10 минут.
    ratelimit(key="ip", rate="3/10m", method="POST", block=True),
    name="dispatch",
)
class RegisterView(APIView):
    """POST /api/users/register/ — регистрация нового пользователя."""

    # Регистрация доступна без аутентификации.
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: User = serializer.save()

        token = services.generate_token(
            user_id=user.pk,
            role_id=user.role_id,
        )

        return Response(
            {
                "message": "Пользователь успешно зарегистрирован.",
                "token": token,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(
    # 5 попыток с одного IP за 1 минуту.
    ratelimit(key="ip", rate="5/m", method="POST", block=True),
    name="dispatch",
)
class LoginView(APIView):
    """POST /api/users/login/ — вход по email и паролю, возвращает JWT."""

    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: User = serializer.validated_data["user"]
        token = services.generate_token(
            user_id=user.pk,
            role_id=user.role_id,
        )

        return Response(
            {
                "message": "Вход выполнен успешно.",
                "token": token,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """POST /api/users/logout/ — выход (на клиенте токен удаляется)."""

    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        # JWT — stateless токены; "выход" означает удаление токена на клиенте.
        # Если нужен server-side blacklist — добавить модель TokenBlacklist.
        if request.my_user is None:
            return Response(
                {"detail": "Требуется аутентификация."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {"message": "Выход выполнен. Удалите токен на клиенте."},
            status=status.HTTP_200_OK,
        )


class ProfileView(APIView):
    """
    GET  /api/users/profile/ — получить профиль текущего пользователя.
    PATCH /api/users/profile/ — обновить данные профиля.
    """

    authentication_classes: list = []
    permission_classes: list = []

    def _get_authenticated_user(
        self, request: Request
    ) -> tuple[User | None, Response | None]:
        """Вспомогательный метод: возвращает пользователя или 401-ответ."""
        user: User | None = request.my_user
        if user is None:
            return None, Response(
                {"detail": "Требуется аутентификация."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return user, None

    def get(self, request: Request) -> Response:
        user, error = self._get_authenticated_user(request)
        if error:
            return error

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    def patch(self, request: Request) -> Response:
        user, error = self._get_authenticated_user(request)
        if error:
            return error

        serializer = UserUpdateSerializer(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        updated_user: User = serializer.update(user, serializer.validated_data)

        return Response(
            {
                "message": "Профиль обновлён.",
                "user": UserSerializer(updated_user).data,
            },
            status=status.HTTP_200_OK,
        )


class SoftDeleteView(APIView):
    """DELETE /api/users/me/ — мягкое удаление: is_active=False + logout."""

    authentication_classes: list = []
    permission_classes: list = []

    def delete(self, request: Request) -> Response:
        user: User | None = request.my_user
        if user is None:
            return Response(
                {"detail": "Требуется аутентификация."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response(
            {"message": "Аккаунт деактивирован. Удалите токен на клиенте."},
            status=status.HTTP_200_OK,
        )
