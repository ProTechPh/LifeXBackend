from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)
from . import views

# Redirect root to login
def redirect_to_login(request):
    return redirect('/login/')

urlpatterns = [
    # Root redirects to login
    path('', redirect_to_login, name='home'),
    
    # Django Admin (default)
    path('admin/', admin.site.urls),
    
    # Web Interfaces
    path('login/', views.login_view, name='login'),
    path('staff/', views.it_staff_dashboard, name='it_staff_dashboard'),
    path('patient/', views.patient_portal, name='patient_portal'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Optional: Blockchain explorer (if you added it)
    # path('explorer/', views.blockchain_explorer, name='blockchain_explorer'),
    
    # API endpoints
    path('api/auth/', include('users.urls')),
    path('api/blockchain/', include('blockchain.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)