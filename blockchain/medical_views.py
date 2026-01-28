from rest_framework import status, generics, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.core.cache import cache
from django.conf import settings

from users.models import Appointment
from .models import MedicalRecord, BlockchainTransaction, AuditLog
from .medical_serializers import (
    PatientRegistrationSerializer,
    PatientListSerializer,
    MedicalRecordUploadSerializer,
    MedicalRecordSerializer,
    AuditLogSerializer,
    PatientApprovalSerializer,
    MedicalRecordEditSerializer,
    RecordApprovalSerializer
)
from users.permissions import (
    IsNurse, 
    IsPatient, 
    IsAdmin, 
    IsReceptionist, 
    IsMedicalStaff,
    CanViewRecords, 
    CanRegisterPatients,
    CanUploadRecords,
    CanApprovePatients,
    CanEditRecords,
    CanApproveRecords
)
from .blockchain_service import BlockchainService
from .utils import generate_document_id, hash_file


def log_action(user, action, resource_type='', resource_id='', details='', request=None):
    """Helper to create audit log"""
    ip_address = '0.0.0.0'
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
            
    AuditLog.objects.create(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details,
        ip_address=ip_address
    )


User = get_user_model()


# ==================== STAFF VIEWS ====================

class PatientRegistrationView(generics.CreateAPIView):
    """Staff can register new patients"""
    permission_classes = [CanRegisterPatients]
    serializer_class = PatientRegistrationSerializer
    
    def perform_create(self, serializer):
        user = serializer.save()
        log_action(
            user=self.request.user, 
            action='REGISTER_PATIENT', 
            resource_type='USER', 
            resource_id=user.id, 
            details=f"Registered patient {user.email}",
            request=self.request
        )


class PatientListView(generics.ListAPIView):
    """List all patients with their medical records count"""
    permission_classes = [IsMedicalStaff | IsAdmin]
    serializer_class = PatientListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        # Optimize query with select_related and prefetch_related to avoid N+1
        return User.objects.filter(role='PATIENT').select_related(
            'department'
        ).prefetch_related('medical_records').order_by('-date_joined')


# ==================== NURSE VIEWS ====================

class UploadMedicalRecordView(APIView):
    """Nurses upload medical records for patients"""
    permission_classes = [CanUploadRecords]
    
    def post(self, request):
        serializer = MedicalRecordUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get patient
        patient_email = serializer.validated_data.pop('patient_email')
        patient = User.objects.get(email=patient_email, role='PATIENT')
        
        # Get uploaded file
        document_file = serializer.validated_data['document_file']
        
        try:
            # Generate document ID
            document_id = generate_document_id()
            
            # Hash the document
            document_hash = hash_file(document_file)
            
            # Register on blockchain
            blockchain_service = BlockchainService()
            tx_result = blockchain_service.register_document(
                user_id=patient.id,
                document_id=document_id,
                document_hash=document_hash,
                document_type=serializer.validated_data['record_type']
            )
            
            # Get blockchain address
            blockchain_address = blockchain_service.get_account_for_user(patient.id)
            
            # Create medical record
            medical_record = MedicalRecord.objects.create(
                patient=patient,
                uploaded_by=request.user,
                document_id=document_id,
                document_hash=document_hash,
                blockchain_address=blockchain_address,
                transaction_hash=tx_result['transaction_hash'],
                block_number=tx_result['block_number'],
                status='CONFIRMED',
                is_verified=True,
                registered_on_blockchain_at=timezone.now(),
                **serializer.validated_data
            )
            
            # Log blockchain transaction
            BlockchainTransaction.objects.create(
                user=patient,
                transaction_type='REGISTER',
                transaction_hash=tx_result['transaction_hash'],
                block_number=tx_result['block_number'],
                gas_used=tx_result['gas_used'],
                status='SUCCESS'
            )
            
            # Log the upload action
            log_action(
                user=request.user,
                action='UPLOAD_RECORD',
                resource_type='MEDICAL_RECORD',
                resource_id=medical_record.id,
                details=f"Uploaded {medical_record.record_type} for patient {patient.email}",
                request=request
            )
            
            return Response({
                'message': 'Medical record uploaded and registered on blockchain successfully',
                'record': MedicalRecordSerializer(medical_record, context={'request': request}).data,
                'blockchain_data': {
                    'transaction_hash': tx_result['transaction_hash'],
                    'block_number': tx_result['block_number'],
                    'gas_used': tx_result['gas_used']
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'error': f'Failed to upload medical record: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientRecordsView(generics.ListAPIView):
    """View all records for a specific patient
    - Receptionist: read-only access
    - Nurse/Doctor: full access
    - Patient: own records only
    """
    permission_classes = [CanViewRecords]
    serializer_class = MedicalRecordSerializer
    
    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        user = self.request.user
        
        # Patients can only view their own records
        if user.role == 'PATIENT':
            return MedicalRecord.objects.filter(patient=user)
        
        # Medical staff can view any patient's records
        return MedicalRecord.objects.filter(patient_id=patient_id)


# ==================== PATIENT VIEWS ====================

class MyMedicalRecordsView(generics.ListAPIView):
    """Patients can view their own medical records"""
    permission_classes = [IsPatient]
    serializer_class = MedicalRecordSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'record_type']
    ordering_fields = ['date_of_service', 'created_at']
    ordering = ['-date_of_service']
    
    def get_queryset(self):
        # Log the view action
        log_action(
            user=self.request.user,
            action='VIEW_RECORDS',
            resource_type='MEDICAL_RECORD',
            details='Viewed own medical records',
            request=self.request
        )
        return MedicalRecord.objects.filter(patient=self.request.user)


class MyMedicalRecordDetailView(generics.RetrieveAPIView):
    """Patients can view a specific medical record"""
    permission_classes = [IsPatient]
    serializer_class = MedicalRecordSerializer
    
    def get_queryset(self):
        return MedicalRecord.objects.filter(patient=self.request.user)


class VerifyMyRecordView(APIView):
    """Patients can verify their medical records on blockchain"""
    permission_classes = [IsPatient]
    
    def post(self, request, record_id):
        try:
            # Get the record
            record = MedicalRecord.objects.get(id=record_id, patient=request.user)
            
            # Open and hash the file
            document_hash = hash_file(record.document_file)
            
            # Verify on blockchain
            blockchain_service = BlockchainService()
            verification_result = blockchain_service.verify_document(
                user_id=request.user.id,
                document_id=record.document_id,
                document_hash=document_hash
            )
            
            # Update record verification status
            record.is_verified = verification_result['is_valid']
            record.save()
            
            # Log verification transaction
            BlockchainTransaction.objects.create(
                user=request.user,
                transaction_type='VERIFY',
                transaction_hash=verification_result['transaction_hash'],
                block_number=verification_result['block_number'],
                gas_used=verification_result['gas_used'],
                status='SUCCESS' if verification_result['is_valid'] else 'FAILED'
            )
            
            # Log the verification action
            log_action(
                user=request.user,
                action='VERIFY_RECORD',
                resource_type='MEDICAL_RECORD',
                resource_id=record.id,
                details=f"Verified record {record.document_id}. Result: {record.is_verified}",
                request=request
            )
            
            return Response({
                'is_valid': verification_result['is_valid'],
                'blockchain_data': verification_result
            }, status=status.HTTP_200_OK)
            
        except MedicalRecord.DoesNotExist:
            return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Verification failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== ADMIN VIEWS ====================

class SystemStatsView(APIView):
    """Admin can view system statistics"""
    permission_classes = [IsAdmin | IsMedicalStaff]
    
    def get(self, request):
        today = timezone.now().date()
        
        # Base stats for everyone
        stats = {
            'patients': {
                'total': User.objects.filter(role='PATIENT').count(),
            },
            'staff': {
                'receptionists': User.objects.filter(role='RECEPTIONIST').count(),
                'nurses': User.objects.filter(role='NURSE').count(),
                'doctors': User.objects.filter(role='DOCTOR').count(),
            },
            'medical_records': {
                'total': MedicalRecord.objects.count(),
                'confirmed': MedicalRecord.objects.filter(status='CONFIRMED').count(),
            }
        }

        # Personalized stats for doctors
        if request.user.role == 'DOCTOR':
            stats['personal'] = {
                'today_appointments': Appointment.objects.filter(
                    doctor=request.user, 
                    appointment_date=today
                ).count(),
                'pending_checkins': Appointment.objects.filter(
                    doctor=request.user,
                    appointment_date=today,
                    status='CHECKED_IN'
                ).count()
            }
        
        return Response(stats, status=status.HTTP_200_OK)
            
            
class AuditLogView(generics.ListAPIView):
    """Admin can view audit logs"""
    permission_classes = [IsAdmin]
    serializer_class = AuditLogSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    
    def get_queryset(self):
        return AuditLog.objects.all()


class DownloadMedicalRecordView(APIView):
    """
    Securely download medical record file and log the action.
    Accessible by: 
    - Patient (own records only)
    - Receptionist (read-only, can print)
    - Nurse/Doctor (full access)
    - Admin (full access)
    """
    permission_classes = [CanViewRecords]
    
    def get(self, request, record_id):
        record = get_object_or_404(MedicalRecord, id=record_id)
        
        # Check permissions based on role
        user = request.user
        
        # Patients can only download their own records
        if user.role == 'PATIENT' and record.patient != user:
            return Response({
                'error': 'You can only access your own medical records'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Log the download
        log_action(
            user=request.user,
            action='DOWNLOAD_RECORD',
            resource_type='MEDICAL_RECORD',
            resource_id=record.id,
            details=f"Downloaded file: {record.document_file.name}",
            request=request
        )
        
        # Serve file
        if record.document_file:
            response = FileResponse(record.document_file.open('rb'))
            response['Content-Disposition'] = f'attachment; filename="{record.document_file.name.split("/")[-1]}"'
            return response
        else:
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)


# ==================== PATIENT APPROVAL WORKFLOW ====================

class PendingPatientsView(generics.ListAPIView):
    """List all patients pending approval"""
    permission_classes = [CanApprovePatients]
    serializer_class = PatientListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        # Optimize query to avoid N+1
        return User.objects.filter(
            role='PATIENT',
            account_status='PENDING'
        ).select_related('department').prefetch_related('medical_records').order_by('-date_joined')


@method_decorator(ratelimit(key='user', rate='20/h', method='POST'), name='dispatch')
class ApprovePatientView(APIView):
    """
    Approve a pending patient registration
    Rate limited to 20 approvals per hour per user
    """
    permission_classes = [CanApprovePatients]
    
    def post(self, request, patient_id):
        try:
            patient = User.objects.get(id=patient_id, role='PATIENT')
            
            if patient.account_status != 'PENDING':
                return Response({
                    'error': 'Patient is not in pending status'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update patient status
            patient.account_status = 'APPROVED'
            patient.save()
            
            # Log the approval
            log_action(
                user=request.user,
                action='APPROVE_PATIENT',
                resource_type='USER',
                resource_id=patient.id,
                details=f'Approved patient registration for {patient.email}',
                request=request
            )
            
            return Response({
                'message': 'Patient approved successfully',
                'patient': PatientListSerializer(patient, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)


class RejectPatientView(APIView):
    """Reject a pending patient registration"""
    permission_classes = [CanApprovePatients]
    
    def post(self, request, patient_id):
        serializer = PatientApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            patient = User.objects.get(id=patient_id, role='PATIENT')
            
            if patient.account_status != 'PENDING':
                return Response({
                    'error': 'Patient is not in pending status'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update patient status
            patient.account_status = 'REJECTED'
            patient.save()
            
            # Log the rejection
            reason = serializer.validated_data.get('reason', '')
            log_action(
                user=request.user,
                action='REJECT_PATIENT',
                resource_type='USER',
                resource_id=patient.id,
                details=f'Rejected patient registration for {patient.email}. Reason: {reason}',
                request=request
            )
            
            return Response({
                'message': 'Patient rejected successfully',
                'patient': PatientListSerializer(patient, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)


# ==================== MEDICAL RECORD EDITING/APPROVAL ====================

class PendingRecordsView(generics.ListAPIView):
    """List all external records pending approval"""
    permission_classes = [CanApproveRecords]
    serializer_class = MedicalRecordSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'patient__email', 'patient__first_name', 'patient__last_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Optimize query with select_related to avoid N+1
        return MedicalRecord.objects.filter(
            is_external=True,
            approval_status='PENDING'
        ).select_related('patient', 'uploaded_by', 'approved_by').order_by('-created_at')


class EditMedicalRecordView(generics.UpdateAPIView):
    """Edit external medical records"""
    permission_classes = [CanEditRecords]
    serializer_class = MedicalRecordEditSerializer
    
    def get_queryset(self):
        # Only allow editing external records
        return MedicalRecord.objects.filter(is_external=True)
    
    def perform_update(self, serializer):
        record = serializer.save()
        
        # If record was previously approved, reset to pending after edit
        if record.approval_status == 'APPROVED':
            record.approval_status = 'PENDING'
            record.approved_by = None
            record.approved_at = None
            record.save()
        
        # Log the edit action
        log_action(
            user=self.request.user,
            action='UPLOAD_RECORD',
            resource_type='MEDICAL_RECORD',
            resource_id=record.id,
            details=f'Edited external record {record.document_id} for patient {record.patient.email}',
            request=self.request
        )


class ApproveMedicalRecordView(APIView):
    """Approve an external medical record"""
    permission_classes = [CanApproveRecords]
    
    def post(self, request, record_id):
        try:
            record = MedicalRecord.objects.get(id=record_id, is_external=True)
            
            if record.approval_status == 'APPROVED':
                return Response({
                    'error': 'Record is already approved'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update record approval status
            record.approval_status = 'APPROVED'
            record.approved_by = request.user
            record.approved_at = timezone.now()
            record.rejection_reason = ''
            record.save()
            
            # Log the approval
            log_action(
                user=request.user,
                action='UPLOAD_RECORD',
                resource_type='MEDICAL_RECORD',
                resource_id=record.id,
                details=f'Approved external record {record.document_id} for patient {record.patient.email}',
                request=request
            )
            
            return Response({
                'message': 'Record approved successfully',
                'record': MedicalRecordSerializer(record, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
        except MedicalRecord.DoesNotExist:
            return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)


class RejectMedicalRecordView(APIView):
    """Reject an external medical record"""
    permission_classes = [CanApproveRecords]
    
    def post(self, request, record_id):
        serializer = RecordApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            record = MedicalRecord.objects.get(id=record_id, is_external=True)
            
            if record.approval_status == 'REJECTED':
                return Response({
                    'error': 'Record is already rejected'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update record approval status
            reason = serializer.validated_data.get('reason', '')
            record.approval_status = 'REJECTED'
            record.approved_by = request.user
            record.approved_at = timezone.now()
            record.rejection_reason = reason
            record.save()
            
            # Log the rejection
            log_action(
                user=request.user,
                action='UPLOAD_RECORD',
                resource_type='MEDICAL_RECORD',
                resource_id=record.id,
                details=f'Rejected external record {record.document_id} for patient {record.patient.email}. Reason: {reason}',
                request=request
            )
            
            return Response({
                'message': 'Record rejected successfully',
                'record': MedicalRecordSerializer(record, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
        except MedicalRecord.DoesNotExist:
            return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)


# ==================== ADMIN MONITORING ====================

class UserActivityView(generics.ListAPIView):
    """View activity logs for a specific user"""
    permission_classes = [IsAdmin]
    serializer_class = AuditLogSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    
    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return AuditLog.objects.filter(user_id=user_id).order_by('-created_at')


class SystemActivityView(generics.ListAPIView):
    """View all system activities with filters"""
    permission_classes = [IsAdmin]
    serializer_class = AuditLogSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__email', 'action', 'details']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = AuditLog.objects.all()
        
        # Optional filters
        action = self.request.query_params.get('action', None)
        user_role = self.request.query_params.get('user_role', None)
        
        if action:
            queryset = queryset.filter(action=action)
        
        if user_role:
            queryset = queryset.filter(user__role=user_role)
        
        return queryset