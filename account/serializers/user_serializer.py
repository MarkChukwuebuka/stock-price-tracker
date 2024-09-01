from password_validator import PasswordValidator
from rest_framework import serializers

from account.models import User


class CreateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class EditUserSerializer(serializers.ModelSerializer):
    role_ids = serializers.ListSerializer(child=serializers.IntegerField())

    class Meta:
        model = User
        fields = ["first_name", "last_name"]


class UserListSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "email", "created_at", "updated_at",
        ]


class ActivateOrDeactivateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class AttachOrDetachUserFromTenantSerializer(serializers.Serializer):
    attach = serializers.BooleanField()



class ChangePasswordSerializer(serializers.Serializer):

    password = serializers.CharField()
    new_password = serializers.CharField(min_length=8, max_length=30)

    def validate(self, attrs):
        data = attrs.copy()

        if data.get("password") == data.get("new_password"):
            raise serializers.ValidationError("Passwords cannot be the same.", "password")

        password_schema = PasswordValidator()
        password_schema.min(8).uppercase().lowercase().digits().symbols()

        if not password_schema.validate(data.get("new_password")):
            raise serializers.ValidationError("New Password is too weak. Password must contain a combination of upper and lower case letters, digits and symbols", "new_password")

        return data
