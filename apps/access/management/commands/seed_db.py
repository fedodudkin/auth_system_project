from django.core.management.base import BaseCommand

from apps.access.models import AccessRoleRule, BusinessElement, Role

# ──────────────────────────────────────────────────────────────
# Конфигурация сидирования — все данные описаны декларативно,
# чтобы команду было легко расширять без правки логики.
# ──────────────────────────────────────────────────────────────

BUSINESS_ELEMENTS: list[str] = [
    "Products",
    "Users",
    "Orders",
    'Roles',
    'AccessRules',
]

# Полный набор булевых полей модели AccessRoleRule.
ALL_PERMISSION_FIELDS = (
    "read",
    "read_all",
    "create",
    "update",
    "update_all",
    "delete",
    "delete_all",
)


def _all_true() -> dict[str, bool]:
    """Возвращает словарь со всеми правами, выставленными в True."""
    return dict.fromkeys(ALL_PERMISSION_FIELDS, True)


def _all_false() -> dict[str, bool]:
    """Возвращает словарь со всеми правами, выставленными в False
    (база по умолчанию)."""
    return dict.fromkeys(ALL_PERMISSION_FIELDS, False)


# Структура: role_name -> element_name -> {поле: значение}
# Указываем только отличия от False; остальное заполнит _all_false().
PERMISSIONS_CONFIG: dict[str, dict[str, dict[str, bool]]] = {
    "Admin": {
        # Администратор имеет полный доступ ко всем элементам.
        "Products": _all_true(),
        "Users": _all_true(),
        "Orders": _all_true(),
        "Roles": _all_true(),
        "AccessRules": _all_true(),
    },
    "Manager": {
        # Менеджер может читать и редактировать продукты, но не удалять.
        "Products": {
            **_all_false(),
            "read": True,
            "read_all": True,
            "update": True,
            "update_all": True,
            "create": True,
        },
        # К пользователям — только чтение.
        "Users": {
            **_all_false(),
            "read": True,
            "read_all": True,
        },
        "Orders": {
            **_all_false(),
            "read": True,
            "read_all": True,
            "create": True,
            "update": True,
        },
    },
    "User": {
        # Рядовой пользователь работает только со своими объектами.
        "Products": {
            **_all_false(),
            "read": True,
            "create": True,
            "update": True,
        },
        # Пользователь может смотреть и редактировать только свой профиль.
        "Users": {
            **_all_false(),
            "read": True,
            "update": True,
        },
        "Orders": {
            **_all_false(),
            "read": True,
            "create": True,
        },
    },
}


class Command(BaseCommand):
    help = "Заполняет БД начальными ролями, бизнес-элементами и правилами доступа."

    def handle(self, *args, **kwargs) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Запуск seed_db ===\n"))

        elements = self._seed_business_elements()
        roles = self._seed_roles()
        self._seed_permissions(roles, elements)

        self.stdout.write(self.style.SUCCESS("\n✓ Сидирование завершено успешно.\n"))

    # ──────────────────────────────────────────────
    # Приватные методы
    # ──────────────────────────────────────────────

    def _seed_business_elements(self) -> dict[str, BusinessElement]:
        """Создаёт бизнес-элементы. Возвращает словарь name -> объект."""
        self.stdout.write(self.style.MIGRATE_LABEL("► Бизнес-элементы:"))
        elements: dict[str, BusinessElement] = {}

        for name in BUSINESS_ELEMENTS:
            obj, created = BusinessElement.objects.get_or_create(name=name)
            elements[name] = obj
            status = (
                self.style.SUCCESS("создан")
                if created
                else self.style.WARNING("уже существует")
            )
            self.stdout.write(f"  [{status}] BusinessElement: {name}")

        return elements

    def _seed_roles(self) -> dict[str, Role]:
        """Создаёт роли. Возвращает словарь name -> объект."""
        self.stdout.write(self.style.MIGRATE_LABEL("\n► Роли:"))
        roles: dict[str, Role] = {}

        for role_name in PERMISSIONS_CONFIG:
            obj, created = Role.objects.get_or_create(name=role_name)
            roles[role_name] = obj
            status = (
                self.style.SUCCESS("создана")
                if created
                else self.style.WARNING("уже существует")
            )
            self.stdout.write(f"  [{status}] Role: {role_name}")

        return roles

    def _seed_permissions(
        self,
        roles: dict[str, Role],
        elements: dict[str, BusinessElement],
    ) -> None:
        """Создаёт или обновляет правила доступа согласно PERMISSIONS_CONFIG."""
        self.stdout.write(
            self.style.MIGRATE_LABEL("\n► Правила доступа (AccessRoleRule):")
        )

        for role_name, element_rules in PERMISSIONS_CONFIG.items():
            role = roles[role_name]

            for element_name, perms in element_rules.items():
                # Пропускаем элементы, которых нет в БД (на случай расхождения конфигов)
                element = elements.get(element_name)
                if element is None:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  [!] Элемент '{element_name}' не найден — пропускаем."
                        )
                    )
                    continue

                _, created = AccessRoleRule.objects.update_or_create(
                    role=role,
                    element=element,
                    defaults=perms,
                )

                action = "создано" if created else "обновлено"
                granted = [f for f, v in perms.items() if v]
                denied = [f for f, v in perms.items() if not v]

                self.stdout.write(
                    f"  [{self.style.SUCCESS(action)}] "
                    f"{role_name:10s} → {element_name:12s} | "
                    f"✓ {', '.join(granted) or '—'}  "
                    f"✗ {', '.join(denied) or '—'}"
                )
