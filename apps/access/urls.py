from django.urls import path

from apps.access import views

app_name = "access"

urlpatterns = [
    path("roles/", views.RoleListView.as_view(), name="role-list"),
    path("rules/", views.AccessRuleListView.as_view(), name="rule-list"),
    path("rules/<int:pk>/", views.AccessRuleDetailView.as_view(), name="rule-detail"),
]

