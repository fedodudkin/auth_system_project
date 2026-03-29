from django.db import models


class Role(models.Model):
    """Роль пользователя в системе (Admin, Manager, User и т.д.)."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "roles"
        verbose_name = "Роль"
        verbose_name_plural = "Роли"

    def __str__(self) -> str:
        return self.name


class BusinessElement(models.Model):
    """Бизнес-объект, доступ к которому регулируется (Users, Products и т.д.)."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "business_elements"
        verbose_name = "Бизнес-элемент"
        verbose_name_plural = "Бизнес-элементы"

    def __str__(self) -> str:
        return self.name


class AccessRoleRule(models.Model):
    """
    Таблица правил доступа: какая роль что может делать с каким бизнес-объектом.

    read      — читать собственный объект
    read_all  — читать все объекты
    create    — создавать объекты
    update    — изменять собственный объект
    update_all — изменять любой объект
    delete    — удалять собственный объект
    delete_all — удалять любой объект
    """

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="access_rules",
    )
    element = models.ForeignKey(
        BusinessElement,
        on_delete=models.CASCADE,
        related_name="access_rules",
    )
    # Права доступа.
    read = models.BooleanField(default=False)
    read_all = models.BooleanField(default=False)
    create = models.BooleanField(default=False)
    update = models.BooleanField(default=False)
    update_all = models.BooleanField(default=False)
    delete = models.BooleanField(default=False)
    delete_all = models.BooleanField(default=False)

    class Meta:
        db_table = "access_role_rules"
        verbose_name = "Правило доступа"
        verbose_name_plural = "Правила доступа"
        # Комбинация роль + элемент должна быть уникальной.
        unique_together = ("role", "element")

    def __str__(self) -> str:
        return f"{self.role.name} → {self.element.name}"