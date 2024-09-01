from django.urls import path

from account.controllers.auth_controller import (
    LoginView, ForgotPasswordRequestView, ResetPasswordRequestView,
    RegisterView, RegisterOtpView, VerifyOtpView, AppTokenRefreshView,
    LogoutView
)

urlpatterns = [
    path('/login', LoginView.as_view()),
    path('/logout', LogoutView.as_view()),
    path('/signup', RegisterView.as_view()),
    path('/signup/resend-otp', RegisterOtpView.as_view()),
    path('/signup/verify-otp', VerifyOtpView.as_view()),
    path('/token/refresh', AppTokenRefreshView.as_view()),

    path('/password/forgot', ForgotPasswordRequestView.as_view()),
    path('/password/change', ResetPasswordRequestView.as_view()),
]
