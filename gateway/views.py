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

import redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

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

class GetData(APIView):
    def get(self, request):
        user_id = request.user
        # check if the request is coming from owner and verify key
        # set rpm and set dq, increment on every request
        # every time a new request comes in, and the minute in redis is 
        # different from the now().minute dont increment, but if the minute is different reset to 0

        now = timezone.now()
        time = now.strftime("%Y%m%d%H%M")
        # what if there are multiple users 
        if r.hgetall(f'user_{user_id}'):
            if time == r.hgetall(f'user_{user_id}'.rpm_time) and r.hgetall(f'user_{user_id}'.rpm_counter) <= 5:
                new_val = r.hget(f'user_{user_id}'.rpm_counter) + 1
                r.hset(f'user_{user_id}'.rpm_counter, new_val)
            elif time == r.hgetall(f'user_{user_id}'.rpm_time) and r.get(f'user_{user_id}'.rpm_counter) > 5:
                return Response({
                    'error': 'max requests per minute hit'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        else:
            r.hset(f'user_{user_id}', mapping={'rpm_time': time, 'rpm_counter': 0})

        day = now.strftime("%Y%m%d")
        if r.hgetall(f'user_{user_id}'):
            if day == r.hgetall(f'user_{user_id}'.qd_day) and r.hgetall(f'user_{user_id}'.qd_day) <= 5:
                new_val = r.hgetall(f'user_{user_id}'.qd_counter) + 1
                r.hset(f'user_{user_id}'.qd_counter, new_val)
            elif day == r.hgetall(f'user_{user_id}'.qd_day) and r.hgetall(f'user_{user_id}'.qd_counter) > 5:
                return Response({
                    'error': 'max daily quota hit'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        else:
            r.hset(f'user_{user_id}', mapping={'dq_day': day, 'dq_counter': 0})

        api_key = request.headers.get('api_key')
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
        try:
            ApiKey.objects.get(key_hash=hashed_key)
            # check if the key is active and its status
            return Response({
                'message': 'api_key found'
            }, status=status.HTTP_200_OK)
        except ApiKey.DoesNotExist:
            return Response({
                'error': 'api_key does not exist'
            }, status=status.HTTP_404_NOT_FOUND)



