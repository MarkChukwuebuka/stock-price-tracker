from rest_framework import serializers

from stock.models import Stock


class CreateStockSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255)
    symbol = serializers.CharField(max_length=255)

    def validate(self, attrs):
        data = attrs.copy()

        data["name"] = data.get('name').strip()
        data["symbol"] = data.get('symbol').strip()

        return data


class StockSerializer(serializers.ModelSerializer):

    class Meta:
        model = Stock
        fields = [
            "id", "name", "symbol"
        ]


class UpdateStockSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True, allow_null=False)
    symbol = serializers.CharField(max_length=255, required=True, allow_null=False)

    def validate(self, attrs):
        data = attrs.copy()

        if data.get('name'):
            data["name"] = data.get('name').strip()

        if data.get('symbol'):
            data["symbol"] = data.get('symbol').strip()

        return data
