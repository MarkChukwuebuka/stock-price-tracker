from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.utils.translation import gettext as _
from email_validator import validate_email
from password_validator import PasswordValidator
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from account.models import User
from account.services.user_service import UserService
from services.log import AppLogger
from services.util import render_template_to_text, format_phone_number


class UserPasswordResetSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(max_length=250, min_length=12)
    new_password = serializers.CharField(max_length=250, min_length=12)

    def validate_username(self, username):
        return username

    def validate_new_password(self, password):
        return password


class LoginSerializer(TokenObtainSerializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
    grant_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    token_class = RefreshToken

    def validate(self, attrs):
        username = attrs.get("username").lower()
        password = attrs.get("password")

        authenticate_kwargs = {
            "username": username,
            "password": password
        }
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        try:
            self.user = authenticate(**authenticate_kwargs)
        except User.MultipleObjectsReturned:
            raise serializers.ValidationError(_("auth.login.mistaken_identity"), "email")

        except Exception as e:
            AppLogger.report(e)
            raise serializers.ValidationError(
                render_template_to_text(_("auth.login.error"), {"error": str(e)}),
                "email"
            )

        if self.user is None:
            raise serializers.ValidationError("Incorrect email/password", "email")

        if self.user.deleted_at:
            raise serializers.ValidationError("User does not exist", "email")

        authentication = self.get_token(self.user)
        return {
            "user": self.user,
            "access_token": str(authentication.access_token),
        }


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=255)

    def validate(self, attrs):
        data = attrs.copy()

        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password", "")

        password_schema = PasswordValidator()
        password_schema.min(8).uppercase().lowercase().digits().symbols()

        if not password_schema.validate(password):
            raise serializers.ValidationError("Password is too weak", "password")

        try:
            email_info = validate_email(email, check_deliverability=True)
            email = email_info.normalized
        except Exception as e:
            raise serializers.ValidationError("Invalid email provided", "email")

        request = self.context.get("request", None)
        user_service = UserService(request)
        user, _ = user_service.find_user_by_email(email)

        if user:
            raise serializers.ValidationError("User account already exist, please proceed to login", "email")

        data["email"] = email
        data["password"] = make_password(password)

        return data


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    class Meta:
        fields = ["email"]


class PasswordSerializer(serializers.Serializer):
    password = serializers.CharField()



class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class ResetPasswordRequestSerializer(serializers.Serializer):
    password = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True)

    def validate(self, attrs):
        data = attrs.copy()

        password = attrs.get("password", "")
        email = attrs.get("email")

        password_schema = PasswordValidator()
        password_schema.min(12).uppercase().lowercase().digits().symbols()

        if not password_schema.validate(password):
            raise serializers.ValidationError("Insecure Password", "password")

        user_service = UserService(None)
        user, error = user_service.find_user_by_email(email)

        data["password"] = password
        data["user"] = user

        return data


