from rest_framework import permissions

class IsFanGroup(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name='Fan').exists()

class IsAdminGroup(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name='Admin').exists()


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        # user must be logged in
        if not request.user.is_authenticated:
            return False

        # check if admin
        if request.user.groups.filter(name='Admin').exists():
            return True
        
        # check if owner
        target_user_id = view.kwargs.get('user_id')
        return str(target_user_id) == str(request.user.id)
