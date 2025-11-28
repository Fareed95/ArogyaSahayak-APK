from django.urls import path
from .views import UserDeetsViewSet,NotificationViewset,getMedicineViewset,PostMedicineView,medicineNotificationViewset

urlpatterns = [
    path('user/', UserDeetsViewSet.as_view()),  
    path('notification/', NotificationViewset.as_view()),  
    path('medicinenotification/', medicineNotificationViewset.as_view()),  
    path('getmedicine/', getMedicineViewset.as_view()),  
    path('postmedicine/', PostMedicineView.as_view()),  
    path('postmedicine/<int:pk>/', PostMedicineView.as_view())
]
