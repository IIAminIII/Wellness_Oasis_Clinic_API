from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(_request):
    return JsonResponse({"status": "ok", "service": "wellness-oasis-api"})


urlpatterns = [
    path("health/", health_check, name="health"),
    path("admin/", admin.site.urls),
    path("contact_us/", include("contact_us.urls")),
    path("services/", include("services.urls")),
    path("patients/", include("patients.urls")),
    path("doctors/", include("doctors.urls")),
    path("appointments/", include("appointments.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
