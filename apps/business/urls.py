from django.urls import path

from apps.business import views

app_name = "business"

urlpatterns = [
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path(
        "products/<int:pk>/",
        views.ProductDetailView.as_view(),
        name="product-detail",
    ),
    path("orders/", views.OrderListView.as_view(), name="order-list"),
]