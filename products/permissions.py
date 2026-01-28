from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit objects.
    Read-only access is allowed for all users.
    
    Used for: Categories, Products
    - GET, HEAD, OPTIONS: Anyone (including unauthenticated)
    - POST, PUT, PATCH, DELETE: Admin users only
    """
    
    def has_permission(self, request, view):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for admin users
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow users to edit their own objects.
    Admins can edit any object.
    
    Used for: Product Reviews
    - GET: Anyone (filtered by view logic)
    - POST: Authenticated users
    - PUT, PATCH, DELETE: Owner or Admin
    """
    
    def has_permission(self, request, view):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions require authentication
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for owner or admin
        return obj.user == request.user or request.user.is_staff


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow authenticated users to create/edit.
    Read-only access for unauthenticated users.
    
    Similar to DRF's built-in IsAuthenticatedOrReadOnly but with custom logic.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return request.user and request.user.is_authenticated
