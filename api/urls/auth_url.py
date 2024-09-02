from django.urls import path

from account.controllers.auth_controller import LoginView, LogoutView, RegisterView, AppTokenRefreshView

urlpatterns = [
    path('login', LoginView.as_view()),
    path('logout', LogoutView.as_view()),
    path('signup', RegisterView.as_view()),
    path('token/refresh', AppTokenRefreshView.as_view()),

]
