from django.urls import path
from .views import DietViewSet

urlpatterns = [
    path('analyze/', DietViewSet.as_view()),
]
