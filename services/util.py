import decimal
import json
import random
import re
import string
from datetime import datetime, date
from functools import wraps
from math import ceil
from typing import Union, TypeVar
from uuid import UUID, uuid4

import phonenumbers
import requests
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AnonymousUser
from django.core.mail import send_mail
from django.db.models import TextChoices
from django.template import Context, Template
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.timezone import make_aware, is_aware
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from account.models import UserTypes, User
from crm.models import Organization, Staff
from idss.decorators import CustomApiPermissionRequired
from idss.errors.app_errors import OperationError
from services.cache_util import CacheUtil
from services.encryption_util import AESCipher
from services.log import AppLogger

T = TypeVar("T")


class HTTPMethods(TextChoices):
    get = "GET"
    post = "POST"
    patch = "PATCH"
    put = "PUT"
    options = "OPTIONS"
    delete = "DELETE"


class AnalyticsDuration(TextChoices):
    Daily = "daily"
    Weekly = "weekly"
    Monthly = "monthly"
    Quarterly = "quarterly"
    Yearly = "yearly"


class CustomAPIResponseUtil:

    def response_with_json(self, data, status_code=None):
        if not status_code:
            status_code = status.HTTP_200_OK

        if not data:
            data = {}
        elif not isinstance(data, dict):
            data = {"data": data}

        if not settings.APP_ENC_ENABLED:
            return Response(data, status=status_code)

        cipher = AESCipher(settings.APP_ENC_KEY, settings.APP_ENC_VEC)
        encrypted_data = cipher.encrypt_nested(data)

        return Response(encrypted_data, status=status_code)

    def response_with_error(self, error_list, status_code=None):
        if not status_code:
            status_code = status.HTTP_400_BAD_REQUEST

        response_errors = {"non_field_errors": []}

        def extract_errors(error_detail):
            if isinstance(error_detail, str):
                response_errors["non_field_errors"].append(error_detail)
            elif isinstance(error_detail, dict):
                for key, value in error_detail.items():
                    response_errors[key] = value if isinstance(value, list) else [value]

        if isinstance(error_list, list):
            for error in error_list:
                extract_errors(error)
        else:
            extract_errors(error_list)

        if not response_errors["non_field_errors"]:
            response_errors.pop("non_field_errors")

        return self.response_with_json(response_errors, status_code=status_code)

    def bad_request(self, message=None, data: dict = None):
        if not data:
            data = {}
        elif not isinstance(data, dict):
            data = {"data": data}

        if message:
            data['message'] = message

        return self.response_with_json({"error": data}, status_code=status.HTTP_400_BAD_REQUEST)

    def response_with_message(self, message, status_code=status.HTTP_200_OK):
        return self.response_with_json({"message": message}, status_code=status_code)

    def validation_error(self, errors, status_code=None):
        if status_code is None:
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

        if isinstance(errors, dict):
            if 'error' in errors:
                nested_errors = errors.pop("error")
                errors.pop("status_code", None)
                for key, value in nested_errors.items():
                    errors.update({key: [value]})
            if 'non_field_errors' in errors:
                nested_errors = errors.pop("non_field_errors")
                AppLogger.print(nested_errors)
                if isinstance(nested_errors, list):
                    for value in nested_errors:
                        if value.code not in errors:
                            errors[value.code] = []
                        errors[value.code].append(value)

        return self.response_with_json({
            "errors": errors
        }, status_code=status_code)


class Util:

    @staticmethod
    def is_valid_password(password):
        return re.match(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@#$%^&+=!]).{8,}$", password)

    @staticmethod
    def get_user_with_roles(user):
        def _user_data_source_callback():
            _data = {
                "id": user.id,
                "permissions": list(user.user_permissions_id()),
                "roles": list(user.roles.values_list('id', flat=True))
            }
            return _data, None

        if user:
            util = CacheUtil()
            cache_key = util.generate_cache_key(user.pk, user.tenant_id, "roles", "permissions")
            data, _ = util.get_cache_value_or_default(cache_key, _user_data_source_callback)
            return data
        else:
            return {"id": None, "permissions": [], "roles": []}

    @staticmethod
    def generate_digits(length):
        digits = '0123456789'
        code = ""
        for _ in range(length):
            code += random.choice(digits)
        return code


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, decimal.Decimal):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        elif hasattr(o, '__dict__'):
            return o.__dict__.get('name', '')
        return super(DecimalEncoder, self).default(o)


class DefaultPagination(PageNumberPagination):
    max_page_size = 1000
    page_size = 100
    page_query_param = "page"
    page_size_query_param = 'page_size'


def render_template_to_text(message, data=dict):
    context = Context(data)
    template = Template(message)

    return template.render(context)


class CustomAPIRequestUtil(DefaultPagination, CacheUtil):
    serializer_class = None

    def __init__(self, request=None):
        self.request = request
        self.current_page = 1

    @property
    def auth_user(self) -> User | None:
        user = self.request.user if self.request and self.request.user else None
        if isinstance(user, AnonymousUser):
            user = None

        return user

    @property
    def is_platform_admin(self) -> bool:
        if not self.auth_user:
            return False

        return self.auth_user.user_type == UserTypes.idss_user

    @property
    def is_staff(self) -> bool:
        if not self.auth_user:
            return False

        return self.auth_user.user_type == UserTypes.organization_staff

    @property
    def is_organization_admin(self) -> bool:
        if not self.auth_user:
            return False

        return self.auth_user.user_type == UserTypes.organization_admin

    @property
    def auth_organization(self) -> Organization | None:
        if not self.auth_user:
            return None

        def _get_rec():
            return self.auth_user.organization, None

        organization, _ = self.get_cache_value_or_default(
            self.generate_cache_key("organization", "user", self.auth_user.id), _get_rec
        )

        return organization

    @property
    def auth_staff(self) -> Staff | None:
        if not self.auth_user:
            return None

        def _get_rec():
            return self.auth_user.staff_record, None

        staff, _ = self.get_cache_value_or_default(
            self.generate_cache_key("organization", "staff", self.auth_user.id), _get_rec)

        return staff

    def report_activity(self, activity_type, data, description=None):
        if not description:
            description = str(activity_type) + " records related to " + type(data).__name__ + ": " + str(
                data.id) + " | " + str(data)
        AppLogger.print(self.auth_user, description)

    def make_error(self, error: str):
        return OperationError(self.request, message=error)

    def make_404(self, error: str):
        return OperationError(self.request, message=error, status_code=status.HTTP_404_NOT_FOUND)

    def make_403(self, error: str):
        return OperationError(self.request, message=error, status_code=status.HTTP_403_FORBIDDEN)

    def make_500(self, exception):
        AppLogger.report(exception)
        return OperationError(
            self.request, message="Operation error: {}".format(str(exception)),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    def get_specific_request_filter_params(self, *additional_params):
        if additional_params is None:
            additional_params = []

        return self.__extract_filter_params(list(additional_params), self.request.query_params)

    def __extract_filter_params(self, general_params, filter_bucket):
        data = {}
        for param in general_params:
            field_value = filter_bucket.get(param, None)
            if field_value is not None:
                if str(field_value).lower() in ['true', 'false']:
                    data[param] = str(filter_bucket.get(param))
                else:
                    data[param] = filter_bucket.get(param) or ''
            else:
                data[param] = None

        return data

    def get_request_filter_params(self, *additional_params):
        general_params = ['keyword', 'filter', 'from_date', 'to_date', 'page', 'page_size']

        data = self.__extract_filter_params(general_params, self.request.query_params)
        data.update(self.get_specific_request_filter_params(*additional_params))

        if data['filter'] and not data['keyword']:
            data['keyword'] = data['filter']

        try:
            data['page'] = int(data.get('page') or 1)

        except Exception as e:
            AppLogger.report(e)
            data['page'] = 1

        try:
            data['page_size'] = int(data.get('page_size') or 100)
        except Exception as e:
            AppLogger.report(e)
            data['page_size'] = 100

        self.current_page = data.get("page")
        self.page_size = data.get("page_size")

        return data

    def get_request_filter_param_list(self, *params):
        data = {}

        filter_bucket = self.request.query_params

        for param in params:
            data[param] = filter_bucket.getlist(param, [])

        return data

    def get_paginated_list_response(self, data, count_all):
        return self.__make_pages(self.__get_pagination_data(count_all, data))

    def is_numeric(self, value):
        if value:
            try:
                numeric_value = float(value)
                return numeric_value
            except (TypeError, ValueError):
                return False
        return False

    def __get_pagination_data(self, total, data):
        prev_page_no = int(self.current_page) - 1
        last_page = ceil(total / self.page_size) if self.page_size > 0 else 0
        has_next_page = total > 0 and len(data) > 0 and total > ((self.page_size * prev_page_no) + len(data))
        has_previous_page = (prev_page_no > 0) and (total >= (self.page_size * prev_page_no))

        return prev_page_no, data, total, last_page, has_next_page, has_previous_page

    def __make_pages(self, pagination_data):
        prev_page_no, data, total, last_page, has_next_page, has_prev_page = pagination_data

        prev_page_url = None
        next_page_url = None

        request_url = self.request.path

        q_list = []
        if has_next_page or has_prev_page:
            query_list = self.request.query_params or {}
            for key in query_list:
                if key != "page":
                    q_list.append(f"{key}={query_list[key]}")

        if has_next_page:
            new_list = q_list.copy()
            new_list.append("page=" + str((+self.current_page + 1)))
            q = "&".join(new_list)
            next_page_url = f"{request_url}?{q}"

        if has_prev_page:
            new_list = q_list.copy()
            new_list.append("page=" + str((+self.current_page - 1)))
            q = "&".join(new_list)
            prev_page_url = f"{request_url}?{q}"

        return {
            "page_size": self.page_size,
            "current_page": self.current_page if self.current_page <= last_page else last_page,
            "last_page": last_page,
            "total": total,
            "next_page_url": next_page_url,
            "prev_page_url": prev_page_url,
            "data": data
        }

    def fetch_list(self, filter_params):
        raise Exception("Not implemented")

    def fetch_paginated_list(self, filter_params):
        queryset = self.fetch_list(filter_params=filter_params)
        page = self.paginate_queryset(queryset, request=self.request)
        data = self.serializer_class(page, many=True).data

        return self.get_paginated_list_response(data, queryset.count())


class CustomApiRequestProcessorBase(CustomApiPermissionRequired, CustomAPIRequestUtil, CustomAPIResponseUtil):
    permission_classes = [IsAuthenticated]

    payload = None
    serializer_class = None

    context: Union[dict, None] = None
    extra_context_data = dict()

    request_serializer_requires_many = False
    request_payload_requires_decryption = False

    response_payload_requires_encryption = False
    response_serializer = None
    response_serializer_requires_many = False
    wrap_response_in_data_object = False

    ref_id = None
    logging_enabled = False

    @property
    def auth_staff(self):
        return self.auth_user.staff_record

    @property
    def auth_user(self):
        return self.request.user if self.request.user else None

    def process_request(self, request, target_function, **extra_args):
        self.check_required_roles_and_permissions()

        if self.request_payload_requires_decryption:
            encryption_util = AESCipher(settings.APP_ENC_KEY, settings.APP_ENC_VEC)
            request_data = encryption_util.decrypt(request.data)
        else:
            request_data = request.data

        if self.logging_enabled:
            self.ref_id = Util.generate_digits(18)
            try:
                from crm.tasks import make_api_request_log
                make_api_request_log(
                    request.user.id if request.user and not request.user.is_anonymous else "",
                    request.data, request.get_full_path(), self.ref_id,
                    headers={k: v for k, v in request.META.items() if k != 'HTTP_AUTHORIZATION'}
                )
            except Exception as e:
                AppLogger.log(e)

        if not self.context:
            self.context = dict()
        self.context['request'] = request
        if self.extra_context_data:
            for key, val in self.extra_context_data.items():
                self.context[key] = val

        try:
            if self.serializer_class and request.method in {"PUT", "POST", "PATCH"}:
                serializer = self.serializer_class(
                    data=request_data, context=self.context,
                    many=self.request_serializer_requires_many
                )

                if serializer.is_valid():
                    response_raw_data: Union[tuple, T] = target_function(serializer.validated_data, **extra_args)
                    return self.__handle_request_response(response_raw_data)
                else:
                    return self.validation_error(serializer.errors)
            else:
                response_raw_data: Union[tuple, T] = target_function(**extra_args)
                return self.__handle_request_response(response_raw_data)
        except Exception as e:
            AppLogger.report(e)
            response_data = {"error": str(e), "message": "Server error"}
            if self.ref_id:
                try:
                    from crm.tasks import update_api_request_log
                    update_api_request_log.delay(self.ref_id, response_status="Success", response_body=response_data)
                except Exception as e:
                    AppLogger.report(e)
            return self.response_with_json(response_data, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def __handle_request_response(self, response_raw_data):
        response_data, error_detail = None, None
        if isinstance(response_raw_data, tuple):
            response_data, error_detail = response_raw_data
        else:
            response_data = response_raw_data

        if error_detail:
            status_code = None
            if isinstance(error_detail, OperationError):
                status_code = error_detail.get_status_code()
                error_detail = error_detail.get_message()

                if self.ref_id:
                    try:
                        from crm.tasks import update_api_request_log
                        update_api_request_log.delay(self.ref_id, response_status="Failed", response_body=error_detail)
                    except Exception as e:
                        AppLogger.report(e, error=error_detail)
            if status_code and status_code in [400, 404, 500]:
                return self.response_with_message(error_detail, status_code=status_code)

            return self.response_with_error(error_detail, status_code)

        if self.response_serializer is not None:
            response_data = self.response_serializer(response_data, many=self.response_serializer_requires_many).data

        if self.wrap_response_in_data_object:
            response_data = {"data": response_data}

        if self.ref_id:
            try:
                from crm.tasks import update_api_request_log
                update_api_request_log.delay(self.ref_id, response_status="Success", response_body=response_data)
            except Exception as e:
                AppLogger.report(e)
                AppLogger.print(response_data)

        if self.response_payload_requires_encryption:
            encryption_util = AESCipher(settings.APP_ENC_KEY, settings.APP_ENC_VEC)
            response_data = encryption_util.encrypt_nested(response_data)

        return self.response_with_json(response_data)


def generate_password():
    letters = ''.join((random.choice(string.ascii_letters) for _ in range(random.randint(10, 15))))
    digits = ''.join((random.choice(string.digits) for _ in range(random.randint(3, 5))))

    sample_list = list(letters + digits)
    random.shuffle(sample_list)
    return ''.join(sample_list)


def generate_username():
    return ''.join((random.choice(string.ascii_lowercase) for _ in range(random.randint(10, 15))))


def generate_ref():
    _id = uuid4().fields

    ref = str(_id[-1]) + str(_id[-2] + _id[-3])

    return ref


def zerofy_number(number):
    return "{:02d}".format(number)


def get_unique_id(prefix=""):
    rand_no = ""
    for i in range(0, 3):
        rand_no += random.choice("0123456789")

    date_to_string = (
            datetime.strftime(timezone.now(), "%Y%m%d%H%M%S") +
            get_random_string(4, allowed_chars='0123456789')
    )

    return f'{prefix}{date_to_string[3:-2]}{rand_no}'


def generate_ref_id(prefix="", length=5):
    rand_no = ""
    for _ in range(0, length):
        rand_no += random.choice("0123456789")

    date_to_string = (
            datetime.strftime(datetime.now(), "%Y%m%d%H%M%S") +
            rand_no
    )

    return f'{prefix}{date_to_string}'


def make_http_request(method, url, headers=None, data=None, json=None):
    methods_dict = {
        HTTPMethods.get: requests.get,
        HTTPMethods.post: requests.post,
        HTTPMethods.patch: requests.patch,
        HTTPMethods.options: requests.options,
        HTTPMethods.delete: requests.delete,
    }

    try:
        request_method = methods_dict.get(method.upper())
        if not request_method:
            return None, f"Unsupported method: {method}"

        if json is not None:
            response = request_method(url, headers=headers, json=json)
        else:
            response = request_method(url, headers=headers, data=data)

        AppLogger.print(response.text)

        try:
            if response.ok:
                return response.json(), None
        except:
            return None, response.text

        return None, f"Request failed with status code: {response.status_code}"
    except Exception as e:
        AppLogger.report(e)
        return None, f"Request error: {str(e)}"


def user_type_required(*user_types):
    def decorator(f):
        @wraps(f)
        def _wrapped_view(view, request, *args, **kwargs):
            if getattr(request.user, 'user_type', None) not in user_types:
                return CustomAPIResponseUtil().response_with_message('Permission denied', status_code=403)

            return f(view, request, *args, **kwargs)

        return _wrapped_view

    return decorator


def permission_or_user_type_required(permission, *user_types):
    def decorator(f):
        @wraps(f)
        def _wrapped_view(view, request, *args, **kwargs):
            user = request.user

            if getattr(request.user, 'user_type', None) not in user_types and not user.has_permission(permission):
                return CustomAPIResponseUtil().response_with_message('Permission denied', status_code=403)

            return f(view, request, *args, **kwargs)

        return _wrapped_view

    return decorator


def generate_otp():
    if settings.DEBUG:
        otp = "123456"
    else:
        otp = str(random.randint(1, 999999)).zfill(6)

    hashed_otp = make_password(otp)

    return otp, hashed_otp


def check_otp_time_expired(expires_at):
    if not is_aware(expires_at):
        expires_at = make_aware(expires_at)

    current_time = timezone.now()

    return current_time > expires_at


def compare_password(input_password, hashed_password):
    return check_password(input_password, hashed_password)


def is_valid_file_extension(file_extension):
    recognized_file_extension_list = [
        ".pdf", ".png", '.jpg', '.jpeg', ".csv", ".doc", ".docx", ".xlsx"
    ]
    return file_extension in recognized_file_extension_list


def format_phone_number(phone_number, region_code=None):
    if not region_code:
        region_code = "NG"
    try:
        x = phonenumbers.parse(phone_number, region_code)
        phone_number = phonenumbers.format_number(x, phonenumbers.PhoneNumberFormat.E164)

        if phonenumbers.is_valid_number_for_region(x, region_code):
            return phone_number
    except:
        pass

    return None


def format_date(date_str):
    try:
        return make_aware(datetime.strptime(date_str, "%Y-%m-%d"))
    except:
        try:
            return make_aware(datetime.strptime(date_str, "%d-%m-%Y"))
        except:
            try:
                return make_aware(datetime.strptime(date_str, "%d/%m/%Y"))
            except:
                return None


def evaluate_formular(formular, **data):
    return eval(formular, data, {})


def send_email(*args, **kwargs):
    return send_mail(*args, **kwargs)


def frange(start, stop, step):
    while start < stop:
        yield start
        start += step
