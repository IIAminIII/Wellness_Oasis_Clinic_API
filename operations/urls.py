from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BedViewSet,
    CurrentActorView,
    DepartmentViewSet,
    FacilityViewSet,
    OperationsDashboardView,
    RoleAssignmentViewSet,
    RoomViewSet,
)


router = DefaultRouter()
router.register("facilities", FacilityViewSet, basename="facility")
router.register("departments", DepartmentViewSet, basename="department")
router.register("rooms", RoomViewSet, basename="room")
router.register("beds", BedViewSet, basename="bed")
router.register("roles", RoleAssignmentViewSet, basename="role-assignment")

urlpatterns = [
    path("", include(router.urls)),
    path("me/", CurrentActorView.as_view(), name="operations-me"),
    path("dashboard/", OperationsDashboardView.as_view(), name="operations-dashboard"),
]
