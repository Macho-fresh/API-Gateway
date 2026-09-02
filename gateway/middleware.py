from rest_framework.response import Response
from rest_framework import status

class ApiMiddleware():
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        key = request.headers.get('API_Key')

        if not key:
            return Response({
                'message': 'api key required'
            }, status=status.HTTP_401_UNAUTHORIZED)

        return self.get_response(request)
        