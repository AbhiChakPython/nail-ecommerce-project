from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views_frontend import RegisterView, CustomLoginView, CustomLogoutView, \
    CustomPasswordChangeView, ProfileView, custom_csrf_failure_view, DeleteAccountView, AdminUserListView, \
    AdminUserDeleteView

app_name = "users"
urlpatterns = [

    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('change_password/', CustomPasswordChangeView.as_view(), name='change_password'),

    path('password_reset/',
         auth_views.PasswordResetView.as_view(
             template_name='users/password_reset.html',
             email_template_name='users/password_reset_email.html',
             success_url=reverse_lazy('users:password_reset_done')
         ),
         name='password_reset'),
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html',
             success_url=reverse_lazy('users:password_reset_complete')
         ),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
         name='password_reset_complete'),

    # Customer delete self account
    path('delete_account/', DeleteAccountView.as_view(), name='delete_account'),

    # Admin user management (list and delete)
    path('admin/users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('admin/users/delete/<int:pk>/', AdminUserDeleteView.as_view(), name='admin_user_delete'),
    path("csrf-failure/", custom_csrf_failure_view, name="csrf_failure"),
]
