from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

admin.site.site_header = "Michango ya Harusi"
admin.site.site_title = "Michango ya Harusi"
admin.site.index_title = "Usimamizi"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ingia/", auth_views.LoginView.as_view(), name="login"),
    path("toka/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("michango.urls")),
]

if settings.STORAGES["default"]["BACKEND"].endswith("FileSystemStorage"):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
