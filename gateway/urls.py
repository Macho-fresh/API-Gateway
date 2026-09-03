from .views import *
from django.urls import path

urlpatterns=[
    path('create-api-key/', CreateApiKey.as_view()),
    path('get-data/', GetData.as_view()),
    path('delete-api-key/', DeleteApiKey.as_view()),
    path('rotate-api-key/', RotateAPIKeyView.as_view()),
    path('request-logs/', RequestLogs.as_view())
]