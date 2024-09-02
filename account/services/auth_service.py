
from django.contrib.auth.models import update_last_login

from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from account.services.user_service import UserService
from services.log import AppLogger
from services.util import CustomAPIRequestUtil


class AuthService(CustomAPIRequestUtil):

    def __init__(self, request):
        super().__init__(request)

    def login(self, payload) -> dict:
        user = payload.get("user")

        access_token = str(payload.get("access_token"))

        email = user.email

        response_data = {
            "access_token": access_token,
            "email": email,
            "full_name":f"{user.first_name} {user.last_name}"
        }

        update_last_login(None, user)
        return dict(data=response_data)


    def register(self, payload):
        user_service = UserService(self.request)

        user, error = user_service.create_single(payload)
        if error:
            return None, error

        token_service = TokenService(self.request)
        access_token = token_service.create_access_token(user)

        payload = {
            "user": user,
            "access_token": access_token
        }

        response_data = self.login(payload)
        response_data.update({"message": "Account was created successfully "})

        return response_data, None


    def logout(self):
        try:
            if not self.auth_user:
                return None, self.make_error("User is not authenticated")

            user = self.auth_user

            for token in OutstandingToken.objects.filter(user=user):
                _, _ = BlacklistedToken.objects.get_or_create(token=token)

            return {"message": "Logout successful"}, None

        except Exception as e:
            AppLogger.report(e)
            return None, self.make_error(str(e))




class TokenService(CustomAPIRequestUtil):

    def create_access_token(self, user, expiry=None):
        token = RefreshToken.for_user(user)

        if expiry is not None:
            token.set_exp(f"{expiry}")

        return str(token.access_token)
