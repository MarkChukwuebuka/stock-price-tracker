from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema
from rest_framework.generics import CreateAPIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from account.serializers.auth_serializer import LoginSerializer, RegisterSerializer, ForgotPasswordRequestSerializer
from account.services.auth_service import AuthService
from crm.serializers.others_serializer import EmptySerializer
from services.util import CustomApiRequestProcessorBase

class LoginView(TokenObtainPairView, CustomApiRequestProcessorBase):
    permission_classes = []
    authentication_classes = []
    serializer_class = LoginSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.login)


class RegisterView(CreateAPIView, CustomApiRequestProcessorBase):
    authentication_classes = []
    permission_classes = []
    serializer_class = RegisterSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.register)


class LogoutView(CreateAPIView, CustomApiRequestProcessorBase):

    @extend_schema(tags=["Auth"])
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.logout)


class AppTokenRefreshView(CreateAPIView, TokenRefreshView):
    serializer_class = EmptySerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key='ip', rate='5/m'))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

