from rest_framework import filters, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from Wellness_Oasis_Clinic.permissions import IsAdminOrReadOnly
from operations.models import RoleAssignment
from operations.permissions import has_any_role
from .models import AvailableTime, Designation, Doctor, Review, Specialization
from .serializers import (
    AvailableTimeSerializer,
    DesignationSerializer,
    DoctorSerializer,
    ReviewSerializer,
    SpecializationSerializer,
)


class DoctorViewSet(viewsets.ModelViewSet):
    serializer_class = DoctorSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "user__first_name",
        "user__last_name",
        "designation__name",
        "specialization__name",
    ]
    ordering_fields = ["fee", "user__first_name"]
    ordering = ["user__first_name"]

    def get_queryset(self):
        return (
            Doctor.objects.select_related("user")
            .prefetch_related("designation", "specialization", "available_time")
            .distinct()
        )


class DesignationViewSet(viewsets.ModelViewSet):
    queryset = Designation.objects.all().order_by("name")
    serializer_class = DesignationSerializer
    permission_classes = [IsAdminOrReadOnly]


class SpecializationViewSet(viewsets.ModelViewSet):
    queryset = Specialization.objects.all().order_by("name")
    serializer_class = SpecializationSerializer
    permission_classes = [IsAdminOrReadOnly]


class AvailableTimeForSpecificDoctor(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        doctor_id = request.query_params.get("doctor_id")
        if doctor_id:
            return queryset.filter(doctor__id=doctor_id).distinct()
        return queryset


class AvailableTimeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    queryset = AvailableTime.objects.all().order_by("name")
    serializer_class = AvailableTimeSerializer
    filter_backends = [AvailableTimeForSpecificDoctor]


class ReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ReviewSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = Review.objects.select_related("reviewer__user", "doctor__user")
        doctor_id = self.request.query_params.get("doctor_id")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        return queryset

    def perform_create(self, serializer):
        patient = getattr(self.request.user, "patient_profile", None)
        if not patient:
            raise ValidationError("A patient profile is required to add a review.")
        serializer.save(reviewer=patient)

    def _ensure_owner(self, instance):
        if (
            not has_any_role(
                self.request.user,
                RoleAssignment.Role.ADMINISTRATOR,
            )
            and instance.reviewer.user_id != self.request.user.id
        ):
            raise PermissionDenied("You can only change your own review.")

    def perform_update(self, serializer):
        self._ensure_owner(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_owner(instance)
        instance.delete()
