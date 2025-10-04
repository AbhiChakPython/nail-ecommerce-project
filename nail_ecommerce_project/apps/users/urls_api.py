from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views_api import (
    RegisterAPIView,
    ProfileAPIView,
    ChangePasswordAPIView,
    LogoutAPIView,
    CustomTokenObtainPairView,
)

app_name = "users_api"

urlpatterns = [

    path('register/', RegisterAPIView.as_view(), name='api_register'),  # POST /api/users/register/
    path('login/', CustomTokenObtainPairView.as_view(), name='api_login'),  # POST /api/users/login/
    path('logout/', LogoutAPIView.as_view(), name='api_logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileAPIView.as_view(), name='api_profile'),  # GET, PUT
    path('change-password/', ChangePasswordAPIView.as_view(), name='api_change_password'),

]