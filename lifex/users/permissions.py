from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permission class for Admin users only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'ADMIN'
        )


class IsITStaff(permissions.BasePermission):
    """Permission class for IT Staff only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['IT_STAFF', 'ADMIN']
        )


class IsPatient(permissions.BasePermission):
    """Permission class for approved patients only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'PATIENT' and
            request.user.account_status == 'APPROVED'
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission class allowing owners to edit their own profile or admins to edit any"""
    
    def has_object_permission(self, request, view, obj):
        # Admins can access any object
        if request.user.role == 'ADMIN':
            return True
        
        # Users can only access their own objects
        return obj == request.user