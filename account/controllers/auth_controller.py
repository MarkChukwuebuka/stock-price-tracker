from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema
from rest_framework.generics import CreateAPIView, DestroyAPIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from account.serializers.auth_serializer import (
    LoginSerializer, ForgotPasswordRequestSerializer, RegisterSerializer,
    VerifyOtpSerializer, ResendOtpSerializer, ResetPasswordRequestSerializer,
    EmailSerializer, VerifyAuthenticatorOtpSerializer, ContactUsSerializer, BookADemoSerializer, PasswordSerializer
)
from account.services.auth_service import AuthService, ContactUsService
from crm.serializers.others_serializer import SimpleResponseMessageSerializer, EmptySerializer
from services.util import CustomApiRequestProcessorBase


class LoginView(TokenObtainPairView, CustomApiRequestProcessorBase):
    permission_classes = []
    authentication_classes = []
    serializer_class = LoginSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)

        requested_user_type = request.query_params.get("claim")
        return self.process_request(request, service.login, requested_user_type=requested_user_type)


class LogoutView(CreateAPIView, CustomApiRequestProcessorBase):

    @extend_schema(tags=["Auth"])
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.logout)


class RegisterView(CreateAPIView, CustomApiRequestProcessorBase):
    authentication_classes = []
    permission_classes = []
    serializer_class = RegisterSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.log_register)


class RegisterOtpView(CreateAPIView, CustomApiRequestProcessorBase):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResendOtpSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.resend_registration_otp)


class VerifyOtpView(CreateAPIView, CustomApiRequestProcessorBase):
    authentication_classes = []
    permission_classes = []
    serializer_class = VerifyOtpSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.verify_register_otp)


class AppTokenRefreshView(CreateAPIView, TokenRefreshView):
    serializer_class = EmptySerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ResetPasswordRequestView(CreateAPIView, CustomApiRequestProcessorBase):
    serializer_class = ResetPasswordRequestSerializer
    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)

        return self.process_request(request, service.reset_password)


class ForgotPasswordRequestView(CreateAPIView, CustomApiRequestProcessorBase):
    serializer_class = ForgotPasswordRequestSerializer

    permission_classes = []
    authentication_classes = []

    @extend_schema(tags=["Auth"])
    def post(self, request, *args, **kwargs):
        service = AuthService(request)

        return self.process_request(request, service.request_password_reset)


class GenerateOTPView(CreateAPIView, CustomApiRequestProcessorBase):
    serializer_class = EmptySerializer

    @extend_schema(tags=["2FA"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)

        return self.process_request(request, service.generate_authenticator_otp)


class Verify2faOTPView(CreateAPIView, CustomApiRequestProcessorBase):
    permission_classes = []
    authentication_classes = []
    serializer_class = VerifyAuthenticatorOtpSerializer

    @extend_schema(tags=["2FA"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)

        return self.process_request(request, service.verify_2fa_otp)


class GenerateEmailOTPView(CreateAPIView, CustomApiRequestProcessorBase):
    serializer_class = EmptySerializer

    @extend_schema(tags=["2FA"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)

        return self.process_request(request, service.generate_email_2fa_otp)


class DisableOTPAPIView(CreateAPIView, CustomApiRequestProcessorBase):
    serializer_class = PasswordSerializer

    @extend_schema(tags=["2FA"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def delete(self, request, *args, **kwargs):
        service = AuthService(request)

        return self.process_request(request, service.disable_2fa)


class ContactUsView(CreateAPIView, CustomApiRequestProcessorBase):
    serializer_class = ContactUsSerializer
    response_serializer = SimpleResponseMessageSerializer
    permission_classes = []
    authentication_classes = []

    @extend_schema(tags=["Contact Us"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = ContactUsService(request)

        return self.process_request(request, service.contact_us)


class BookDemoView(CreateAPIView, CustomApiRequestProcessorBase):
    serializer_class = BookADemoSerializer
    response_serializer = SimpleResponseMessageSerializer
    permission_classes = []
    authentication_classes = []

    @extend_schema(tags=["Contact Us"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = ContactUsService(request)

        return self.process_request(request, service.book_demo)
