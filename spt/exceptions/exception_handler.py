from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if response.status_code not in [200, 201] and 'detail' in response.data:
            if 'code' in response.data and response.data.get("code") == "user_not_found":
                message = "Request authorization failed"
            else:
                message = response.data['detail']

            data = {'message': message}
            response.data = data

    return response



class RateLimitException(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too many requests, try again later"
