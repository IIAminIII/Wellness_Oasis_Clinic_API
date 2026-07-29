from rest_framework.permissions import BasePermission, SAFE_METHODS

from operations.models import RoleAssignment
from operations.permissions import has_any_role


class IsAdminOrReadOnly(BasePermission):
    """Public reads with writes restricted to hospital administrators."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or (
            request.user.is_authenticated
            and has_any_role(
                request.user,
                RoleAssignment.Role.ADMINISTRATOR,
            )
        )


class CreateOrAdminOnly(BasePermission):
    """Allow public create, but keep submitted records private to staff."""

    def has_permission(self, request, view):
        if request.method == "POST":
            return True
        return request.user.is_authenticated and has_any_role(
            request.user,
            RoleAssignment.Role.ADMINISTRATOR,
        )
