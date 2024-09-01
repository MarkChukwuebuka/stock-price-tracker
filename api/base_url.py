from django.urls import path, include



urlpatterns = [
    path("auth", include("api.urls.auth_url")),

    path("account/", include("api.urls.account_url")),

]