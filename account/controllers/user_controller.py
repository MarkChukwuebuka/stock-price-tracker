from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException
from rest_framework.generics import RetrieveUpdateDestroyAPIView, ListCreateAPIView

from account.models import UserTypes
from account.serializers.user_serializer import CreateUserSerializer, EditUserSerializer, UserSerializer
from account.services.user_service import UserService
from crm.serializers.others_serializer import PaginatedResponseSerializer
from services.util import CustomApiRequestProcessorBase, user_type_required


class ListCreateUsersApiView(ListCreateAPIView, CustomApiRequestProcessorBase):
    serializer_class = CreateUserSerializer

    @extend_schema(tags=["Users"])
    @user_type_required(UserTypes.super_admin)
    def get(self, request, *args, **k):
        filter_params = self.get_request_filter_params("user_type", "status")
        self.response_serializer = PaginatedResponseSerializer

        service = UserService(request)
        return self.process_request(request, service.fetch_paginated_list, filter_params=filter_params)

    @extend_schema(tags=["Users"])
    def post(self, request, *args, **kwargs):
        self.wrap_response_in_data_object = True

        self.response_serializer = UserSerializer

        service = UserService(request)
        return self.process_request(request, service.create_single)


class RetrieveUpdateOrDeleteUserApiView(RetrieveUpdateDestroyAPIView, CustomApiRequestProcessorBase):
    serializer_class = EditUserSerializer
    response_serializer = UserSerializer
    wrap_response_in_data_object = True

    @extend_schema(tags=["Users"])
    def patch(self, request, *args, **kwargs):
        raise APIException("Not implemented")

    @extend_schema(tags=["Users"])
    def get(self, request, *args, **kwargs):

        service = UserService(request)

        return self.process_request(request, service.fetch_single_by_id, user_id=kwargs.get("user_id"))

    @extend_schema(tags=["Users"])
    def put(self, request, *args, **kwargs):

        service = UserService(request)
        return self.process_request(request, service.update_single)

    @extend_schema(tags=["Users"])
    @user_type_required(UserTypes.super_admin)
    def delete(self, request, *args, **kwargs):
        self.serializer_class = None

        service = UserService(request)
        return self.process_request(request, service.delete_single, user_id=kwargs.get("user_id"))

