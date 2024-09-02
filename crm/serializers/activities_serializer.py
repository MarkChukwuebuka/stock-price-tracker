from rest_framework import serializers

from crm.models import Activity


class ActivitySerializer(serializers.ModelSerializer):

    class Meta:
        model = Activity
        fields = [
            "id", "activity_type", "note", "created_at"
        ]
