import json

from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.access.middleware import JWTAuthMiddleware
from apps.access.models import Role
from apps.users import services
from apps.users.models import User

# ──────────────────────────────────────────────────────────────
# Вспомогательные фабрики
# ──────────────────────────────────────────────────────────────


def make_user(
    email: str = "test@example.com",
    name: str = "Test User",
    password: str = "securepass123",
    role: Role | None = None,
    is_active: bool = True,
) -> User:
    """Фабрика пользователей для тестов."""
    return User.objects.create(
        email=email,
        name=name,
        password_hash=services.hash_password(password),
        role=role,
        is_active=is_active,
    )


def make_role(name: str = "User") -> Role:
    """Фабрика ролей."""
    role, _ = Role.objects.get_or_create(name=name)
    return role


def auth_header(user: User) -> dict[str, str]:
    """Генерирует заголовок Authorization для запросов."""
    token = services.generate_token(user_id=user.pk, role_id=user.role_id)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════
# 1. Тесты регистрации
# ══════════════════════════════════════════════════════════════


class RegistrationTests(TestCase):
    def setUp(self) -> None:
        self.url = reverse("users:register")
        self.valid_payload = {
            "name": "Alice",
            "email": "alice@example.com",
            "password": "strongpass99",
            "password_confirmation": "strongpass99",
        }

    def test_registration_success_returns_201(self) -> None:
        """Успешная регистрация возвращает 201 и JWT-токен."""
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("token", response.json())

    def test_password_is_hashed_in_database(self) -> None:
        """Пароль в БД должен быть хэшем bcrypt, а не открытым текстом."""
        self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/json",
        )
        user = User.objects.get(email=self.valid_payload["email"])
        
        self.assertTrue(user.password_hash.startswith("$2b$"))
        self.assertNotEqual(user.password_hash, self.valid_payload["password"])

    def test_password_hash_is_verifiable(self) -> None:
        """Сохранённый хэш должен успешно верифицироваться через services."""
        self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/json",
        )
        user = User.objects.get(email=self.valid_payload["email"])
        self.assertTrue(
            services.verify_password(self.valid_payload["password"], user.password_hash)
        )

    def test_duplicate_email_returns_400(self) -> None:
        """Повторная регистрация с тем же email должна вернуть 400."""
        make_user(email=self.valid_payload["email"])
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_required_fields_returns_400(self) -> None:
        """Запрос без обязательных полей возвращает 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({"email": "x@x.com"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_short_password_returns_400(self) -> None:
        """Пароль короче 8 символов должен отклоняться."""
        payload = {**self.valid_payload, "password": "123"}
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_password_confirmation_mismatch_returns_400(self) -> None:
        """Несовпадение паролей должно вернуть 400."""
        payload = {**self.valid_payload, "password_confirmation": "differentpass"}
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password_confirmation", response.json())

# ══════════════════════════════════════════════════════════════
# 2. Тесты логина
# ══════════════════════════════════════════════════════════════


class LoginTests(TestCase):
    def setUp(self) -> None:
        self.url = reverse("users:login")
        self.password = "mypassword42"
        self.user = make_user(email="bob@example.com", password=self.password)

    def test_login_success_returns_token(self) -> None:
        """Успешный логин возвращает 200 и JWT-токен."""
        response = self.client.post(
            self.url,
            data=json.dumps({"email": "bob@example.com", "password": self.password}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        # Токен должен быть непустой строкой.
        self.assertIsInstance(data["token"], str)
        self.assertGreater(len(data["token"]), 0)

    def test_token_is_decodable(self) -> None:
        """Возвращённый токен должен успешно декодироваться и содержать user id."""
        response = self.client.post(
            self.url,
            data=json.dumps({"email": "bob@example.com", "password": self.password}),
            content_type="application/json",
        )
        token = response.json()["token"]
        payload = services.decode_token(token)
        self.assertEqual(payload["sub"], self.user.pk)

    def test_wrong_password_returns_400(self) -> None:
        """Неверный пароль должен вернуть 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({"email": "bob@example.com", "password": "wrongpass"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_email_returns_400(self) -> None:
        """Логин с несуществующим email должен вернуть 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({"email": "ghost@example.com", "password": "pass"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_inactive_user_cannot_login(self) -> None:
        """Деактивированный пользователь не должен проходить аутентификацию."""
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            self.url,
            data=json.dumps({"email": "bob@example.com", "password": self.password}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


# ══════════════════════════════════════════════════════════════
# 3. Тесты Middleware
# ══════════════════════════════════════════════════════════════


class JWTMiddlewareTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.user = make_user(email="carol@example.com")

        # Простая заглушка для get_response.
        self.dummy_response = lambda req: None
        self.middleware = JWTAuthMiddleware(self.dummy_response)

    def _make_request(self, token: str | None = None):
        """Создаёт GET-запрос с опциональным Bearer-токеном."""
        request = self.factory.get("/fake/")
        if token:
            request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return request

    def test_valid_token_attaches_user(self) -> None:
        """Валидный токен должен прикрепить пользователя к request.my_user."""
        token = services.generate_token(self.user.pk, self.user.role_id)
        request = self._make_request(token)
        self.middleware(request)

        self.assertIsNotNone(request.my_user)
        self.assertEqual(request.my_user.pk, self.user.pk)

    def test_no_token_sets_my_user_to_none(self) -> None:
        """Запрос без заголовка Authorization → request.my_user = None."""
        request = self._make_request()
        self.middleware(request)
        self.assertIsNone(request.my_user)

    def test_invalid_token_sets_my_user_to_none(self) -> None:
        """Некорректный токен → request.my_user = None."""
        request = self._make_request("this.is.not.a.valid.token")
        self.middleware(request)
        self.assertIsNone(request.my_user)

    def test_expired_token_sets_jwt_expired_flag(self) -> None:
        """Просроченный токен должен выставить флаг request._jwt_expired = True."""
        from datetime import datetime, timedelta, timezone
        import jwt
        from django.conf import settings

        expired_payload = {
            "sub": str(self.user.pk),
            "role_id": None,
            "iat": datetime.now(tz=timezone.utc) - timedelta(hours=48),
            "exp": datetime.now(tz=timezone.utc) - timedelta(hours=24),
        }
        expired_token = jwt.encode(
            expired_payload, settings.JWT_SECRET, algorithm="HS256"
        )

        request = self._make_request(expired_token)
        self.middleware(request)

        self.assertIsNone(request.my_user)
        self.assertTrue(getattr(request, "_jwt_expired", False))

    def test_inactive_user_token_sets_my_user_to_none(self) -> None:
        """Токен деактивированного пользователя → request.my_user = None."""
        self.user.is_active = False
        self.user.save()

        token = services.generate_token(self.user.pk, self.user.role_id)
        request = self._make_request(token)
        self.middleware(request)

        self.assertIsNone(request.my_user)

    def test_token_without_bearer_prefix_is_ignored(self) -> None:
        """Заголовок без префикса 'Bearer ' должен игнорироваться."""
        token = services.generate_token(self.user.pk, self.user.role_id)
        request = self.factory.get("/fake/")
        request.META["HTTP_AUTHORIZATION"] = token
        self.middleware(request)

        self.assertIsNone(request.my_user)


# ══════════════════════════════════════════════════════════════
# 4. Тесты профиля
# ══════════════════════════════════════════════════════════════


class ProfileTests(TestCase):
    def setUp(self) -> None:
        self.url = reverse("users:profile")
        self.user = make_user(email="dave@example.com")

    def test_profile_returns_user_data(self) -> None:
        """Аутентифицированный пользователь получает свои данные."""
        response = self.client.get(self.url, **auth_header(self.user))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], self.user.email)
        self.assertEqual(data["name"], self.user.name)
        self.assertNotIn("password_hash", data)

    def test_profile_requires_authentication(self) -> None:
        """Запрос без токена должен вернуть 401."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_profile_patch_updates_name(self) -> None:
        """PATCH обновляет имя пользователя."""
        response = self.client.patch(
            self.url,
            data=json.dumps({"name": "New Name"}),
            content_type="application/json",
            **auth_header(self.user),
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "New Name")


# ══════════════════════════════════════════════════════════════
# 5. Тесты мягкого удаления
# ══════════════════════════════════════════════════════════════


class SoftDeleteTests(TestCase):
    def setUp(self) -> None:
        self.delete_url = reverse("users:soft-delete")
        self.login_url = reverse("users:login")
        self.password = "deletepass99"
        self.user = make_user(email="eve@example.com", password=self.password)

    def test_soft_delete_sets_is_active_false(self) -> None:
        """После DELETE пользователь должен иметь is_active=False."""
        response = self.client.delete(self.delete_url, **auth_header(self.user))
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_deleted_user_cannot_login(self) -> None:
        """После мягкого удаления пользователь не может войти."""
        self.client.delete(self.delete_url, **auth_header(self.user))

        login_response = self.client.post(
            self.login_url,
            data=json.dumps({"email": "eve@example.com", "password": self.password}),
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 400)

    def test_soft_delete_requires_authentication(self) -> None:
        """Запрос без токена должен вернуть 401."""
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, 401)

    def test_soft_delete_does_not_remove_from_database(self) -> None:
        """Мягкое удаление не должно физически удалять запись из БД."""
        self.client.delete(self.delete_url, **auth_header(self.user))
        # Пользователь всё ещё существует в БД.
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
