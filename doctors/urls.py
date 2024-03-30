from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views 

router = DefaultRouter()

router.register('list', views.DoctorViewSet)
router.register('specialization', views.SpecializationViewSet)
router.register('designation', views.DesignationViewSet)
router.register('reviews', views.ReviewViewSet)
router.register('availableTime', views.AvailableTimeViewSet)
urlpatterns = [
    path('', include(router.urls)),
]