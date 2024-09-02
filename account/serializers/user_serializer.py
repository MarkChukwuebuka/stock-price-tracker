from password_validator import PasswordValidator
from rest_framework import serializers

from account.models import User


class CreateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class EditUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ["first_name", "last_name"]


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "email", "created_at", "updated_at",
        ]

