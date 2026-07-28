from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOrReadOnly(BasePermission):
    """Public reads with writes restricted to Django staff."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or (
            request.user.is_authenticated and request.user.is_staff
        )


class CreateOrAdminOnly(BasePermission):
    """Allow public create, but keep submitted records private to staff."""

    def has_permission(self, request, view):
        if request.method == "POST":
            return True
        return request.user.is_authenticated and request.user.is_staff
