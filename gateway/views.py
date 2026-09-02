from django.shortcuts import render
from .models import *
from rest_framework.views import APIView
from accounts.models import User
from rest_framework.response import Response
from rest_framework import status

import secrets
import hashlib
from django.utils import timezone
from datetime import timedelta

class CreateApiKey(APIView):
    def post(self, request): 
        name = request.data.get('name')
        user_id = request.user

        prefix = 'mc_'
        api_key = prefix + secrets.token_hex(8)
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

        now = timezone.now()
        plan_duration = timedelta(minutes=10)
        expires_at = now + plan_duration

        user = User.objects.get(id = user_id)

        ApiKey.objects.create(
            user = user,
            key_hash = hashed_key,
            name = name,
            expires_at = expires_at
        )

        return Response({
            'api_key': api_key
        }, status=status.HTTP_201_CREATED)

