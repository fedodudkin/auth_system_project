from typing import Optional

from django.http import HttpRequest, JsonResponse

from apps.access.models import AccessRoleRule


# Допустимые действия — совпадают с полями модели AccessRoleRule.
PERMISSION_FIELDS = {
    "read",
    "read_all",
    "create",
    "update",
    "update_all",
    "delete",
    "delete_all",
}


class RBACPermission:
    """
    Базовый класс проверки прав доступа по таблице AccessRoleRule.

    Использование в View:
        permission = RBACPermission(element_name="Products", action="read_all")
        error = permission.check(request)
        if error:
            return error
    """

    def __init__(self, element_name: str, action: str) -> None:
        if action not in PERMISSION_FIELDS:
            raise ValueError(
                f"Недопустимое действие '{action}'. "
                f"Разрешены: {PERMISSION_FIELDS}"
            )
        self.element_name = element_name
        self.action = action

    def check(self, request: HttpRequest) -> Optional[JsonResponse]:
        """
        Проверяем права текущего пользователя.

        Возвращает JsonResponse с ошибкой (401/403) или None, если доступ разрешён.
        """
        user = getattr(request, "my_user", None)

        # 401 — пользователь не аутентифицирован.
        if user is None:
            expired = getattr(request, "_jwt_expired", False)
            message = "Токен истёк." if expired else "Требуется аутентификация."
            return JsonResponse({"detail": message}, status=401)

        # Если у пользователя нет роли — доступ запрещён.
        if user.role is None:
            return JsonResponse(
                {"detail": "У пользователя не назначена роль."}, status=403
            )

        # Ищем правило для данной роли и бизнес-элемента.
        try:
            rule = AccessRoleRule.objects.get(
                role=user.role,
                element__name=self.element_name,
            )
        except AccessRoleRule.DoesNotExist:
            return JsonResponse(
                {"detail": f"Доступ к '{self.element_name}' запрещён."}, status=403
            )

        # Проверяем конкретное право.
        if not getattr(rule, self.action, False):
            return JsonResponse(
                {
                    "detail": (
                        f"Недостаточно прав: '{self.action}' "
                        f"для '{self.element_name}'."
                    )
                },
                status=403,
            )

        return None  # Доступ разрешён.


def require_permission(element_name: str, action: str):
    """
    Декоратор для View-функций. Автоматически проверяет права
    и возвращает 401/403 при их отсутствии.

    Пример:
        @require_permission("Products", "read_all")
        def product_list(request):
            ...
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            perm = RBACPermission(element_name=element_name, action=action)
            error = perm.check(request)
            if error:
                return error
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator