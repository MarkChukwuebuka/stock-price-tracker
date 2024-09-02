
from django.db.models import Q, QuerySet
from django.utils import timezone

from account.models import User
from account.serializers.user_serializer import UserSerializer
from crm.models import ActivityType
from services.util import CustomAPIRequestUtil, compare_password


class UserService(CustomAPIRequestUtil):
    serializer_class = UserSerializer

    def is_super_user(self, user):
        return user.is_superuser

    def delete_single(self, user_id):

        user, error = self.fetch_single_by_id(user_id)
        if error:
            return None, error

        if user == self.auth_user:
            return None, self.make_error("Invalid operation.")

        user.deleted_at = timezone.now()
        user.deleted_by = self.auth_user
        user.save()

        self.clear_temp_cache(user)
        self.report_activity(ActivityType.delete, user)

        return user, None

    def hard_delete(self, user):
        """
        Call function at own risk, delete will actually delete without any check.
        Therefore, use with caution!
        """
        user.delete()

        self.clear_temp_cache(user)
        self.report_activity(ActivityType.delete, user)

        return user, None

    def create_single(self, payload):

        email = payload.get("email")

        existing, error = self.find_user_by_email(email=email)
        if existing:
            return None, self.make_error("User with email already exists")


        first_name = payload.get("first_name")
        last_name = payload.get("last_name")
        password = payload.get("password")

        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            created_at=timezone.now()
        )

        user.set_password(password)

        user.created_by = user
        user.save()

        # TODO: send verification email

        self.report_activity(ActivityType.create, user)

        return user, None

    def update_single(self, payload, user_id=None):
        if user_id:
            user, error = self.fetch_single_by_id(user_id)
            if error:
                return None, error
        else:
            user = self.auth_user

        user.first_name = payload.get("first_name") or user.first_name
        user.last_name = payload.get("last_name") or user.last_name
        user.updated_by = user
        user.updated_at = timezone.now()
        user.save()

        self.clear_temp_cache(user)
        self.report_activity(ActivityType.update, user)

        return user, None


    def find_user_by_email(self, email):
        def __fetch():
            user = self.__get_base_query().filter(email__iexact=email).first()
            if not user:
                return None, self.make_404(f"User with email '{email}' not found")
            return user, None

        cache_key = self.generate_cache_key("user_email", email.lower())
        return self.get_cache_value_or_default(cache_key, __fetch)

    def change_password(self, payload):
        user = self.auth_user

        if not compare_password(payload.get("password"), user.password):
            return None, self.make_error("Access denied, invalid password.")

        user.set_password(payload.get("new_password"))
        user.save()

        return "Password changed successfully."


    def fetch_single_by_id(self, user_id=None):
        def __fetch():
            if self.is_super_admin:
                user = self.__get_base_query().filter(pk=user_id).first()
                if not user:
                    return None, self.make_404("User not found")
            else:
                user = self.auth_user

            return user, None

        cache_key = self.generate_cache_key("user_id", user_id)
        return self.get_cache_value_or_default(cache_key, __fetch)

    def fetch_list(self, filter_params) -> QuerySet:
        self.page_size = filter_params.get("page_size", 100)
        filter_keyword = filter_params.get("keyword")

        q = Q()
        if filter_keyword:
            q &= (Q(first_name__icontains=filter_keyword) | Q(last_name__icontains=filter_keyword) |
                  Q(email__icontains=filter_keyword)
                  )

        return self.__get_base_query().filter(q).exclude(
            pk=self.auth_user.pk
        ).order_by("-created_at")

    @classmethod
    def __get_base_query(cls):
        return User.available_objects

    def clear_temp_cache(self, user):
        self.clear_cache(self.generate_cache_key("user_id", user.id))
        self.clear_cache(self.generate_cache_key("user_email", user.email.lower()))
