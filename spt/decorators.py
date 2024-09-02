import hashlib

from django.contrib.auth.mixins import AccessMixin
from rest_framework import status
from rest_framework.exceptions import APIException


class PermissionDenied(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = {
        "message": 'You do not have permission to perform this action.'
    }
    default_code = 'permission_denied'


class AppAccessMixin(AccessMixin):
    def handle_no_permission(self):
        raise PermissionDenied()


class ActiveUserPermission(AppAccessMixin):

    def has_permission(self):
        if not self.request.user.is_anonymous and self.request.user.deactivated_at is None:
            return True

        return False

    def check_required_roles_and_permissions(self):
        if not self.has_permission():
            return self.handle_no_permission()

