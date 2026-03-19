from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Only admin users"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsStudent(BasePermission):
    """Only student users"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'student'


class IsAdminOrReadOwn(BasePermission):
    """Admin can do anything; students can only read their own data"""
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        return hasattr(obj, 'student') and obj.student == request.user
