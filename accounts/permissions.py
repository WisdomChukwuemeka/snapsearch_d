from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Allows access if:
    1. Django user has is_staff=True (set from Clerk role), OR
    2. Raw JWT payload has role=admin (immediate fallback before DB saves)
    """
    message = "Admin access required"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Primary check — Django flag
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Fallback — raw JWT payload
        payload = request.auth
        if isinstance(payload, dict) and payload.get("role") == "admin":
            return True

        return False