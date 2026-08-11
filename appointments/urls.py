from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views 

router = DefaultRouter()

router.register('list', views.AppointmentViewSet, basename='appointment')
router.register('waitlist', views.WaitlistEntryViewSet, basename='waitlist')
urlpatterns = [
    path('', include(router.urls)),
]
