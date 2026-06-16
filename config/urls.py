from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("auth/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("condominiums/", include("apps.core.urls")),
    path("communication/", include("apps.communication.urls")),
    path("tickets/", include("apps.tickets.urls")),
    path("documents/", include("apps.documents.urls")),
    path("reservations/", include("apps.reservations.urls")),
    path("", include("apps.dashboard.urls")),
]
