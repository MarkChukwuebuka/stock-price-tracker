from django.conf import settings
from django.contrib import admin
from django.urls import path, include

from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('restricted-path/', admin.site.urls),
    path('api/v1/', include("api.base_url")),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]


urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
