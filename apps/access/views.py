from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.models import AccessRoleRule, Role
from apps.access.permissions import RBACPermission
from apps.access.serializers import (
    AccessRoleRuleSerializer,
    AccessRoleRuleUpdateSerializer,
)


class RoleListView(APIView):
    """GET /api/access/roles/ — список всех ролей (только Admin)."""

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request: Request) -> Response:
        perm = RBACPermission(element_name="Roles", action="read_all")
        if error := perm.check(request):
            return error

        roles = Role.objects.values("id", "name", "description")
        return Response(list(roles))


class AccessRuleListView(APIView):
    """
    GET  /api/access/rules/ — список всех правил доступа (Admin).
    POST /api/access/rules/ — создать новое правило (Admin).
    """

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request: Request) -> Response:
        perm = RBACPermission(element_name="AccessRules", action="read_all")
        if error := perm.check(request):
            return error

        rules = AccessRoleRule.objects.select_related("role", "element").all()
        return Response(AccessRoleRuleSerializer(rules, many=True).data)

    def post(self, request: Request) -> Response:
        perm = RBACPermission(element_name="AccessRules", action="create")
        if error := perm.check(request):
            return error

        serializer = AccessRoleRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Проверяем уникальность пары role + element.
        role_id = serializer.validated_data["role"].pk
        element_id = serializer.validated_data["element"].pk

        if AccessRoleRule.objects.filter(
            role_id=role_id, element_id=element_id
        ).exists():
            return Response(
                {"detail": "Правило для этой пары role + element уже существует."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rule = serializer.save()
        return Response(
            AccessRoleRuleSerializer(rule).data,
            status=status.HTTP_201_CREATED,
        )


class AccessRuleDetailView(APIView):
    """
    GET    /api/access/rules/<id>/ — детали правила (Admin).
    PATCH  /api/access/rules/<id>/ — изменить булевые права (Admin).
    DELETE /api/access/rules/<id>/ — удалить правило (Admin).
    """

    authentication_classes: list = []
    permission_classes: list = []

    def _get_rule(self, pk: int) -> AccessRoleRule | None:
        try:
            return AccessRoleRule.objects.select_related("role", "element").get(pk=pk)
        except AccessRoleRule.DoesNotExist:
            return None

    def get(self, request: Request, pk: int) -> Response:
        perm = RBACPermission(element_name="AccessRules", action="read")
        if error := perm.check(request):
            return error

        rule = self._get_rule(pk)
        if rule is None:
            return Response(
                {"detail": "Правило не найдено."}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(AccessRoleRuleSerializer(rule).data)

    def patch(self, request: Request, pk: int) -> Response:
        perm = RBACPermission(element_name="AccessRules", action="update_all")
        if error := perm.check(request):
            return error

        rule = self._get_rule(pk)
        if rule is None:
            return Response(
                {"detail": "Правило не найдено."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = AccessRoleRuleUpdateSerializer(
            rule, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        return Response(AccessRoleRuleSerializer(updated).data)

    def delete(self, request: Request, pk: int) -> Response:
        perm = RBACPermission(element_name="AccessRules", action="delete_all")
        if error := perm.check(request):
            return error

        rule = self._get_rule(pk)
        if rule is None:
            return Response(
                {"detail": "Правило не найдено."}, status=status.HTTP_404_NOT_FOUND
            )

        rule.delete()
        return Response({"detail": "Правило удалено."}, status=status.HTTP_200_OK)
