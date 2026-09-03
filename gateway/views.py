from django.shortcuts import render
from .models import *
from rest_framework.views import APIView
from accounts.models import User
from rest_framework.response import Response
from rest_framework import status
from .serializer import LogSerializer

import secrets
import hashlib
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated

import redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

class CreateApiKey(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request): 
        name = request.data.get('name')
        user_id = request.user.id
        print(user_id)

        prefix = 'mc_'
        api_key = prefix + secrets.token_hex(8)
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

        now = timezone.now()
        plan_duration = timedelta(minutes=30)
        expires_at = timezone.localtime(now) + plan_duration
        print(expires_at)
        print(timezone.localtime(now))

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
        user_id = request.user.id
        api_key = request.headers.get('api_key')
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

        # check if the key is expired
        user = User.objects.get(id=user_id)
        
        key = ApiKey.objects.get(key_hash=hashed_key, user=user, is_active=True)
        print(key.expires_at)
        if timezone.now() >= key.expires_at:
            key.is_active = False
            key.save()
            return Response({
                'error': 'Key has expired'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # check if the request is coming from owner and verify key
        # set rpm and set dq, increment on every request
        # every time a new request comes in, and the minute in redis is 
        # different from the now().minute dont increment, but if the minute is different reset to 0
        n = timezone.now()
        now = timezone.localtime(n)
        time = now.strftime("%Y%m%d%H%M")
        # what if there are multiple users 
        if r.exists(f'key_{hashed_key}'):
            if time == r.hget(f'key_{hashed_key}', 'rpm_time') and int(r.hget(f'key_{hashed_key}', 'rpm_counter')) < 5:
                new_val = int(r.hget(f'key_{hashed_key}', 'rpm_counter')) + 1
                r.hset(f'key_{hashed_key}', 'rpm_counter', new_val)
            elif time == r.hget(f'key_{hashed_key}', 'rpm_time') and int(r.hget(f'key_{hashed_key}', 'rpm_counter')) >= 5:
                return Response({
                    'error': 'max requests per minute hit'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            elif time != r.hget(f'key_{hashed_key}', 'rpm_time'):
                r.hset(f'key_{hashed_key}', mapping={
                    'rpm_time': time,
                    'rpm_counter': 1
                })
        else:
            r.hset(f'key_{hashed_key}', mapping={'rpm_time': time, 'rpm_counter': 1})
        print(r.hgetall(f'key_{hashed_key}'))

        day = now.strftime("%Y%m%d")
        if r.exists(f'key_{hashed_key}', 'qd_day'):
            if day == r.hget(f'key_{hashed_key}', 'dq_day') and int( r.hget(f'key_{hashed_key}', 'dq_day')) <= 5:
                new_val = int(r.hget(f'key_{hashed_key}', 'dq_counter')) + 1
                r.hset(f'key_{hashed_key}', 'dq_counter', new_val)

            elif day == r.hget(f'key_{hashed_key}', 'dq_day') and int(r.hget(f'key_{hashed_key}', 'dq_counter')) > 5:
                return Response({
                    'error': 'max daily quota hit'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            elif day != r.hget(f'key_{hashed_key}', 'qd_day'):
                r.hset(f'key_{hashed_key}', mapping={
                    'qd_day': day,
                    'qd_counter': 1
                })
        else:
            r.hset(f'key_{hashed_key}', mapping={'dq_day': day, 'dq_counter': 1})

        
        user = User.objects.get(id=user_id)
        try:
            ApiKey.objects.get(key_hash=hashed_key, user=user, is_active=True)
            # check if the key is active and its status
            return Response({
                'message': 'api_key found'
            }, status=status.HTTP_200_OK)
        except ApiKey.DoesNotExist:
            return Response({
                'error': 'api_key does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

class RequestLogs(APIView):
    def get(self, request):
        key = request.headers.get('API-Key')
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        k = ApiKey.objects.get(key_hash=hashed_key)
        logs = RequestLog.objects.filter(api_key = k)
        serializer = LogSerializer(logs, many=True)

        return Response({
            'data': serializer.data
        }, status=status.HTTP_200_OK)

class DeleteApiKey(APIView):
    def delete(self, request):
        api_key = request.headers.get('api_key')
        user_id = request.user
        user = User.objects.get(id=user_id)

        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
        try:
            key = ApiKey.objects.get(key_hash=hashed_key, user=user)
            key.delete()
            return Response({
                'message': 'api_key deleted'
            }, status=status.HTTP_200_OK)
        except ApiKey.DoesNotExist:
            return Response({
                'error': 'api_key does not exist'
            }, status=status.HTTP_404_NOT_FOUND)


class RotateAPIKeyView(APIView):

    def post(self, request):
        k = request.data.get('api_key')
        key_hash = hashlib.sha256(k.encode()).hexdigest()
        try:
            api_key = ApiKey.objects.get(key_hash=key_hash)

        except ApiKey.DoesNotExist:
            return Response(
                {"message": "API key not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        prefix = 'mc_'
        key = prefix + secrets.token_hex(8)
        api_key.key_hash = hashlib.sha256(key.encode()).hexdigest()

        api_key.save()

        return Response({
            "message": "API key rotated successfully",
            "api_key": key
        })
