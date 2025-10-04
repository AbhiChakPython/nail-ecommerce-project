from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 🔧 Admin
    path('admin/', admin.site.urls),

    # 🔄 Live reload (for development)
    path("__reload__/", include("django_browser_reload.urls")),

    # 🌐 Core homepage
    path('', include('nail_ecommerce_project.apps.core.urls_frontend', namespace='core')),

    # 👤 Users
    path('users/', include('nail_ecommerce_project.apps.users.urls_frontend', namespace='users')),
    path('api/users/', include('nail_ecommerce_project.apps.users.urls_api', namespace='users_api')),

    # 💅 Services
    path('services/', include('nail_ecommerce_project.apps.services.urls_frontend', namespace='services')),
    path('api/services/', include('nail_ecommerce_project.apps.services.urls_api', namespace='services_api')),

    # 📅 Bookings
    path('bookings/', include('nail_ecommerce_project.apps.bookings.urls_frontend', namespace='bookings')),
    path('api/bookings/', include('nail_ecommerce_project.apps.bookings.urls_api', namespace='bookings_api')),

    # 🛍️ Products
    path('products/', include('nail_ecommerce_project.apps.products.urls_frontend', namespace='products')),
    path('api/products/', include('nail_ecommerce_project.apps.products.urls_api', namespace='products_api')),

    # 📦 Orders
    path('orders/', include('nail_ecommerce_project.apps.orders.urls_frontend', namespace='orders')),
    path('api/orders/', include('nail_ecommerce_project.apps.orders.urls_api', namespace='orders_api')),

    # 📊 Analytics - Admin Dashboard
    path('analytics/', include('nail_ecommerce_project.apps.analytics.urls_frontend', namespace='analytics')),

    # 📦 Admin Manage Orders
    path('manage/orders/', include('nail_ecommerce_project.apps.orders.urls_admin', namespace='orders_admin')),

    # 📅 Admin Manage Bookings
    path('manage/bookings/', include('nail_ecommerce_project.apps.bookings.urls_admin', namespace='bookings_admin')),

]

# 🖼️ Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 🚨 Global error handlers (module-level, outside urlpatterns)
handler400 = 'nail_ecommerce_project.apps.users.views_frontend.custom_bad_request_view'
handler401 = 'nail_ecommerce_project.apps.users.views_frontend.custom_unauthorized_view'
handler403 = 'nail_ecommerce_project.apps.users.views_frontend.custom_permission_denied_view'
handler404 = 'nail_ecommerce_project.apps.users.views_frontend.custom_page_not_found_view'
handler500 = 'nail_ecommerce_project.apps.users.views_frontend.custom_server_error_view'