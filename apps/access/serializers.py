from rest_framework import serializers

from apps.access.models import AccessRoleRule


class AccessRoleRuleSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра и создания правил доступа."""

    role_name = serializers.StringRelatedField(source="role", read_only=True)
    element_name = serializers.StringRelatedField(source="element", read_only=True)

    class Meta:
        model = AccessRoleRule
        fields = (
            "id",
            "role",
            "role_name",
            "element",
            "element_name",
            "read",
            "read_all",
            "create",
            "update",
            "update_all",
            "delete",
            "delete_all",
        )


class AccessRoleRuleUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для частичного обновления правил (только булевые поля)."""

    class Meta:
        model = AccessRoleRule
        fields = (
            "read",
            "read_all",
            "create",
            "update",
            "update_all",
            "delete",
            "delete_all",
        )
