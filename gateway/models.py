from django.db import models
from django.conf import settings

class ApiKey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    key_hash = models.CharField(max_length=100)

    name = models.CharField(max_length=20)

    requests_per_minute = models.IntegerField(default=5)

    daily_quota = models.IntegerField(default=10)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )