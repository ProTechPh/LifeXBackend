from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permission class for Admin users only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'ADMIN'
        )


class IsReceptionist(permissions.BasePermission):
    """Permission class for Medical Receptionist only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'RECEPTIONIST'
        )


class IsNurse(permissions.BasePermission):
    """Permission class for Nurses only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'NURSE'
        )


class IsDoctor(permissions.BasePermission):
    """Permission class for Doctors only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'DOCTOR'
        )


class IsPatient(permissions.BasePermission):
    """Permission class for patients only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'PATIENT'
        )


class IsMedicalStaff(permissions.BasePermission):
    """Permission class for any medical staff (receptionist, nurse, or doctor)"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['RECEPTIONIST', 'NURSE', 'DOCTOR']
        )


class IsAdminOrMedicalStaff(permissions.BasePermission):
    """Permission class for Admin or any medical staff"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'RECEPTIONIST', 'NURSE', 'DOCTOR']
        )


class CanUploadRecords(permissions.BasePermission):
    """Permission class for users who can upload medical records (nurses only)"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'NURSE'
        )


class CanViewRecords(permissions.BasePermission):
    """Permission class for users who can view medical records
    Receptionist: read-only (can view and print)
    Nurse: can upload
    Doctor: can view all
    Patient: can view own records
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin can view all
        if request.user.role == 'ADMIN':
            return True
        
        # Medical staff can view records
        if request.user.role in ['RECEPTIONIST', 'NURSE', 'DOCTOR']:
            return True
        
        # Patients can view their own
        if request.user.role == 'PATIENT':
            return True
        
        return False


class CanManageAppointments(permissions.BasePermission):
    """Permission class for users who can manage appointments
    Receptionist: can create and manage appointments
    Doctor: can view their own appointments
    Patient: can view their own appointments
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin, Receptionist, Nurse, Doctor have access
        if request.user.role in ['ADMIN', 'RECEPTIONIST', 'NURSE', 'DOCTOR']:
            return True
        
        # Patients can only view their own appointments (checked at object level)
        if request.user.role == 'PATIENT':
            return True
        
        return False


class CanRegisterPatients(permissions.BasePermission):
    """Permission class for users who can register new patients (receptionists only)"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['RECEPTIONIST', 'ADMIN']
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission class allowing owners to access their own data or admins to access any"""
    
    def has_object_permission(self, request, view, obj):
        # Admins can access any object
        if request.user.role == 'ADMIN':
            return True
        
        # Users can only access their own objects
        return obj == request.user


class IsPatientOwnerOrMedicalStaff(permissions.BasePermission):
    """Permission for accessing patient-specific resources
    - Patients can only access their own resources
    - Medical staff can access based on their role
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin has full access
        if request.user.role == 'ADMIN':
            return True
        
        # Medical staff can access any patient's resources
        if request.user.role in ['NURSE', 'DOCTOR']:
            return True
        
        # Receptionist can view (read-only) any patient's resources
        if request.user.role == 'RECEPTIONIST':
            # Only allow safe methods (GET, HEAD, OPTIONS)
            return request.method in permissions.SAFE_METHODS
        
        # Check if the object has a patient attribute
        if hasattr(obj, 'patient'):
            return obj.patient == request.user
        
        # Patients can only access their own objects
        return obj == request.user


class CanViewDoctorSchedule(permissions.BasePermission):
    """Permission for viewing doctor schedules
    - Receptionist: can view all doctors in their department
    - Doctor: can view and manage their own schedule
    - Patient: can view available slots (limited)
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin has full access
        if request.user.role == 'ADMIN':
            return True
        
        # Receptionist can view doctors' schedules
        if request.user.role == 'RECEPTIONIST':
            return True
        
        # Doctors can view/manage their schedules
        if request.user.role == 'DOCTOR':
            return True
        
        # Patients can view available slots (for booking)
        if request.user.role == 'PATIENT':
            return request.method in permissions.SAFE_METHODS
        
        return False


class CanApprovePatients(permissions.BasePermission):
    """Permission for users who can approve patient registrations"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'RECEPTIONIST']
        )


class CanEditRecords(permissions.BasePermission):
    """Permission for users who can edit external medical records"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['NURSE', 'DOCTOR']
        )


class CanApproveRecords(permissions.BasePermission):
    """Permission for users who can approve external medical records"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['NURSE', 'DOCTOR']
        )