from django.urls import path
from .views import UploadReportView, UserChatBotAPIView, UserReportInstancesView

urlpatterns = [
    path('report/', UploadReportView.as_view()),  
    path('chatbot/', UserChatBotAPIView.as_view()),
     path("get_user_instances/", UserReportInstancesView.as_view(), name="get_user_instances"),
     path("get_user_instances/<pk>", UserReportInstancesView.as_view(), name="get_user_instances"),

]