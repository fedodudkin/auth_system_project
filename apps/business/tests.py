import json

from django.test import Client, TestCase
from django.urls import reverse

from apps.access.models import AccessRoleRule, BusinessElement, Role
from apps.users import services
from apps.users.models import User

# ──────────────────────────────────────────────────────────────
# Вспомогательные утилиты
# ──────────────────────────────────────────────────────────────


def make_user(email: str, role: Role | None = None) -> User:
    return User.objects.create(
        email=email,
        name="Test",
        password_hash=services.hash_password("pass1234"),
        role=role,
        is_active=True,
    )


def make_authenticated_client(user: User) -> Client:
    """
    Возвращает тестовый Client с Bearer-токеном текущего пользователя.
    Каждый запрос этого клиента автоматически включает заголовок Authorization.
    """
    token = services.generate_token(user_id=user.pk, role_id=user.role_id)
    return Client(HTTP_AUTHORIZATION=f"Bearer {token}")


def setup_rbac(
    role_name: str,
    element_name: str,
    permissions: dict[str, bool],
) -> tuple[Role, BusinessElement]:
    """Создаёт роль, бизнес-элемент и правило доступа одним вызовом."""
    role, _ = Role.objects.get_or_create(name=role_name)
    element, _ = BusinessElement.objects.get_or_create(name=element_name)

    defaults = {
        "read": False,
        "read_all": False,
        "create": False,
        "update": False,
        "update_all": False,
        "delete": False,
        "delete_all": False,
        **permissions,
    }
    AccessRoleRule.objects.update_or_create(
        role=role, element=element, defaults=defaults
    )
    return role, element


# ══════════════════════════════════════════════════════════════
# 1. Тесты RBAC для Products
# ══════════════════════════════════════════════════════════════


class ProductRBACTests(TestCase):
    def setUp(self) -> None:
        self.list_url = reverse("business:product-list")
        self.detail_url = lambda pk: reverse("business:product-detail", args=[pk])

        # Роль User: только read/create/update, без read_all и delete.
        self.user_role, _ = setup_rbac(
            "User",
            "Products",
            {"read": True, "create": True, "update": True},
        )
        # Роль Admin: полный доступ.
        self.admin_role, _ = setup_rbac(
            "Admin",
            "Products",
            {
                "read": True,
                "read_all": True,
                "create": True,
                "update": True,
                "update_all": True,
                "delete": True,
                "delete_all": True,
            },
        )

        self.regular_user = make_user("user@example.com", role=self.user_role)
        self.admin_user = make_user("admin@example.com", role=self.admin_role)
        self.no_role_user = make_user("norole@example.com", role=None)

        # Каждый клиент уже содержит Bearer-токен своего пользователя.
        self.user_client = make_authenticated_client(self.regular_user)
        self.admin_client = make_authenticated_client(self.admin_user)
        self.no_role_client = make_authenticated_client(self.no_role_user)
        # Клиент без токена — для проверки 401.
        self.anon_client = Client()

    # ── Список продуктов (read_all) ────────────────────────────

    def test_admin_can_list_products(self) -> None:
        """Admin с read_all=True получает 200 на список продуктов."""
        response = self.admin_client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_list_all_products(self) -> None:
        """User с read_all=False получает 403 на список продуктов."""
        response = self.user_client.get(self.list_url)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_list_returns_401(self) -> None:
        """Запрос без токена возвращает 401."""
        response = self.anon_client.get(self.list_url)
        self.assertEqual(response.status_code, 401)

    def test_user_without_role_gets_403(self) -> None:
        """Пользователь без роли получает 403."""
        response = self.no_role_client.get(self.list_url)
        self.assertEqual(response.status_code, 403)

    # ── Детали продукта (read) ─────────────────────────────────

    def test_user_can_read_single_product(self) -> None:
        """User с read=True может получить отдельный продукт (200)."""
        response = self.user_client.get(self.detail_url(1))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_read_single_product(self) -> None:
        """Admin может получить отдельный продукт (200)."""
        response = self.admin_client.get(self.detail_url(1))
        self.assertEqual(response.status_code, 200)

    # ── Обновление продукта (update_all) ──────────────────────

    def test_admin_can_update_any_product(self) -> None:
        """Admin с update_all=True может обновить любой продукт."""
        response = self.admin_client.put(
            self.detail_url(1),
            data=json.dumps({"name": "Updated"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_update_all_products(self) -> None:
        """User с update_all=False получает 403 при попытке обновить продукт."""
        response = self.user_client.put(
            self.detail_url(1),
            data=json.dumps({"name": "Hack"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    # ── Удаление продукта (delete_all) ────────────────────────

    def test_admin_can_delete_product(self) -> None:
        """Admin с delete_all=True может удалить продукт."""
        response = self.admin_client.delete(self.detail_url(1))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_delete_product(self) -> None:
        """User с delete_all=False получает 403 при попытке удалить продукт."""
        response = self.user_client.delete(self.detail_url(1))
        self.assertEqual(response.status_code, 403)


# ══════════════════════════════════════════════════════════════
# 2. Тесты RBAC для Orders
# ══════════════════════════════════════════════════════════════


class OrderRBACTests(TestCase):
    def setUp(self) -> None:
        self.list_url = reverse("business:order-list")

        self.manager_role, _ = setup_rbac(
            "Manager",
            "Orders",
            {"read": True, "read_all": True, "create": True},
        )
        self.user_role, _ = setup_rbac(
            "User",
            "Orders",
            {"read": True, "create": True},
        )

        self.manager = make_user("manager@example.com", role=self.manager_role)
        self.user = make_user("user@example.com", role=self.user_role)

        self.manager_client = make_authenticated_client(self.manager)
        self.user_client = make_authenticated_client(self.user)

    def test_manager_can_list_orders(self) -> None:
        """Manager с read_all=True видит список заказов."""
        response = self.manager_client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_list_all_orders(self) -> None:
        """User с read_all=False получает 403 на список заказов."""
        response = self.user_client.get(self.list_url)
        self.assertEqual(response.status_code, 403)


# ══════════════════════════════════════════════════════════════
# 3. Граничные случаи RBAC
# ══════════════════════════════════════════════════════════════


class RBACEdgeCaseTests(TestCase):
    def setUp(self) -> None:
        self.list_url = reverse("business:product-list")

        self.empty_role, _ = Role.objects.get_or_create(name="Guest")
        self.guest_user = make_user("guest@example.com", role=self.empty_role)

        self.guest_client = make_authenticated_client(self.guest_user)
        self.anon_client = Client()

    def test_role_without_rules_gets_403(self) -> None:
        """Роль без записи в AccessRoleRule для элемента получает 403."""
        response = self.guest_client.get(self.list_url)
        self.assertEqual(response.status_code, 403)

    def test_error_response_contains_detail_key(self) -> None:
        """Ответы с ошибками должны содержать ключ 'detail'."""
        res_401 = self.anon_client.get(self.list_url)
        self.assertIn("detail", res_401.json())

        res_403 = self.guest_client.get(self.list_url)
        self.assertIn("detail", res_403.json())

    def test_403_does_not_leak_internal_details(self) -> None:
        """Ответ 403 не должен раскрывать внутреннюю структуру БД."""
        response = self.guest_client.get(self.list_url)
        detail = response.json().get("detail", "")
        self.assertNotIn("AccessRoleRule", detail)
        self.assertNotIn("SELECT", detail)
