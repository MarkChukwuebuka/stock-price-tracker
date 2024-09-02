from django.urls import path, include



urlpatterns = [
    path("auth/", include("api.urls.auth_url")),
    path('users/', include("api.urls.user_url")),

]