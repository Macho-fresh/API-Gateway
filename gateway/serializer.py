from .models import RequestLog
from rest_framework import serializers

class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestLog
        fields = '__all__'