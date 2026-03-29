from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import RBACPermission, require_permission


class ProductListView(APIView):
    """GET /api/business/products/ — список продуктов (read_all)."""

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request: Request) -> Response:
        perm = RBACPermission(element_name="Products", action="read_all")
        if error := perm.check(request):
            return error

        # Мок-данные для демонстрации
        products = [
            {"id": 1, "name": "Ноутбук", "price": 80000},
            {"id": 2, "name": "Монитор", "price": 25000},
        ]
        return Response(products)


class ProductDetailView(APIView):
    """
    GET    /api/business/products/<pk>/ — детали продукта (read).
    PUT    /api/business/products/<pk>/ — обновление (update_all).
    DELETE /api/business/products/<pk>/ — удаление (delete_all).
    """

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request: Request, pk: int) -> Response:
        perm = RBACPermission(element_name="Products", action="read")
        if error := perm.check(request):
            return error

        return Response({"id": pk, "name": "Ноутбук", "price": 80000})

    def put(self, request: Request, pk: int) -> Response:
        perm = RBACPermission(element_name="Products", action="update_all")
        if error := perm.check(request):
            return error

        return Response({"id": pk, "message": "Продукт обновлён (мок)."})

    def delete(self, request: Request, pk: int) -> Response:
        perm = RBACPermission(element_name="Products", action="delete_all")
        if error := perm.check(request):
            return error

        return Response({"id": pk, "message": "Продукт удалён (мок)."})


class OrderListView(APIView):
    """GET /api/business/orders/ — список заказов (read_all)."""

    authentication_classes: list = []
    permission_classes: list = []

    @staticmethod
    @require_permission("Orders", "read_all")  # Демонстрация декоратора
    def get(request: Request) -> Response:
        orders = [
            {"id": 1, "product": "Ноутбук", "status": "pending"},
            {"id": 2, "product": "Монитор", "status": "shipped"},
        ]
        return Response(orders)
