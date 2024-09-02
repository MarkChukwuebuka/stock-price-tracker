from typing import TypeVar, List, Any

from rest_framework import serializers

T = TypeVar("T")


class PaginatedResponseSerializer(serializers.Serializer):
    data = serializers.SerializerMethodField()
    page_size = serializers.IntegerField(default=0)
    current_page = serializers.IntegerField(default=0)
    last_page = serializers.IntegerField(default=0)
    total = serializers.IntegerField(default=0)
    next_page_url = serializers.URLField(required=False, default=None)
    prev_page_url = serializers.URLField(required=False, default=None)

    def get_data(self, obj) -> List[Any]:
        return obj.get("data") if isinstance(obj, dict) else obj.data


class EmptySerializer(serializers.Serializer):
    pass


class SimpleResponseMessageSerializer(serializers.Serializer):
    message = serializers.SerializerMethodField()

    def get_message(self, obj):
        return obj
