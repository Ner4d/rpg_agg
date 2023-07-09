from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from news.views import IndexView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', IndexView.as_view(), name='index'),
    path('users/', include('users.urls', namespace='users')),
    path('news/', include('news.urls', namespace='news')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
