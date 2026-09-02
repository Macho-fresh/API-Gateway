from django.db import models
from django.conf import settings

class ApiKey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key_hash = models.CharField(max_length=100)