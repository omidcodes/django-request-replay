from rest_framework import serializers

from django.conf import settings
from .models import DjangoRequestsHistoryModel


class DjangoRequestsHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DjangoRequestsHistoryModel
        fields = settings.DJANGO_REQUESTS_HISTORY_VISIBLE_COLUMNS
