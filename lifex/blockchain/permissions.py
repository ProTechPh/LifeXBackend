from rest_framework import permissions


class IsITStaff(permissions.BasePermission):
    """Permission for IT_STAFF and ADMIN only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['IT_STAFF', 'ADMIN']
        )


class IsPatient(permissions.BasePermission):
    """Permission for PATIENT users only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'PATIENT'
        )


class IsAdmin(permissions.BasePermission):
    """Permission for ADMIN only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'ADMIN'
        )
