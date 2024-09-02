from rest_framework import status


class OperationError(object):

    def __init__(self, request=None, message=None, status_code=None):
        self.request = request
        self.message = message
        self.status_code = status_code

    def get_message(self):
        return self.message

    def get_status_code(self):
        if self.status_code is None:
            return status.HTTP_400_BAD_REQUEST

        try:
            return int(self.status_code)
        except:
            return status.HTTP_400_BAD_REQUEST

    def __str__(self):
        return self.message
