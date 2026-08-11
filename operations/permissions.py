from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import RoleAssignment


def active_roles(user):
    if not user or not user.is_authenticated:
        return set()
    return set(
        user.role_assignments.filter(is_active=True).values_list("role", flat=True)
    )


def has_any_role(user, *roles):
    return bool(active_roles(user).intersection(roles))


class HasHospitalRole(BasePermission):
    def has_permission(self, request, view):
        allowed_roles = getattr(view, "allowed_roles", ())
        return request.user.is_authenticated and has_any_role(
            request.user,
            *allowed_roles,
        )


class IsHospitalAdministrator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and has_any_role(
            request.user,
            RoleAssignment.Role.ADMINISTRATOR,
        )


class IsWardStaffOrReadOnly(BasePermission):
    """Bed state is changed at the bedside, so nurses need write access too."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and has_any_role(
            request.user,
            RoleAssignment.Role.NURSE,
            RoleAssignment.Role.RECEPTIONIST,
            RoleAssignment.Role.ADMINISTRATOR,
        )


class IsAdministratorOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and has_any_role(
            request.user,
            RoleAssignment.Role.ADMINISTRATOR,
        )
