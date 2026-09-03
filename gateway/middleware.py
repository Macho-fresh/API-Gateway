from django.http import JsonResponse
from .models import RequestLog, ApiKey
import hashlib

class ApiMiddleware():
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        public_paths = [
            '/api/auth/register/',
            '/api/auth/login/',
            '/api/create-api-key/',
            '/admin/login/',
            '/admin/',
            '/admin/accounts/user/'
        ]

        if request.path in public_paths:
            return self.get_response(request)

        key = request.headers.get('API_Key')

        if not key:
            return JsonResponse(
                {'message': 'api key required'},
                status=401
            )
        
        response = self.get_response(request)
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        api_key = ApiKey.objects.get(key_hash = hashed_key)

        RequestLog.objects.create(
            api_key=api_key,
            method=request.method,
            path=request.path,
            status_code=response.status_code
        )

        return response
        