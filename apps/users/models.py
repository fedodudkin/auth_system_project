from django.db import models


class User(models.Model):
    """Кастомная модель пользователя без использования AbstractUser."""

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    # Храним хэш пароля (bcrypt), а не сам пароль.
    password_hash = models.CharField(max_length=255)
    # Внешний ключ на роль; NULL допустим до назначения роли.
    role = models.ForeignKey(
        "access.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"