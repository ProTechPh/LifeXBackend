from rest_framework import status, generics, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q

from .models import MedicalRecord, BlockchainTransaction
from .medical_serializers import (
    PatientRegistrationSerializer,
    PatientListSerializer,
    MedicalRecordUploadSerializer,
    MedicalRecordSerializer,
    PatientApprovalSerializer
)
from .permissions import IsITStaff, IsPatient, IsAdmin
from .blockchain_service import BlockchainService
from .utils import generate_document_id, hash_file

User = get_user_model()


# ==================== IT STAFF VIEWS ====================

class RegisterPatientView(APIView):
    """IT Staff can register new patients"""
    permission_classes = [IsITStaff]
    
    def post(self, request):
        serializer = PatientRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        patient = serializer.save()
        
        return Response({
            'message': 'Patient registered successfully. Pending admin approval.',
            'patient': PatientListSerializer(patient).data
        }, status=status.HTTP_201_CREATED)


class ListPatientsView(generics.ListAPIView):
    """IT Staff can view all patients"""
    permission_classes = [IsITStaff]
    serializer_class = PatientListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'email']
    
    def get_queryset(self):
        queryset = User.objects.filter(role='PATIENT')
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(account_status=status_filter)
        
        return queryset


class UploadMedicalRecordView(APIView):
    """IT Staff uploads medical records for patients"""
    permission_classes = [IsITStaff]
    
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
    """IT Staff can view all records for a specific patient"""
    permission_classes = [IsITStaff]
    serializer_class = MedicalRecordSerializer
    
    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
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
            record.document_file.open('rb')
            current_hash = hash_file(record.document_file)
            record.document_file.close()
            
            # Verify on blockchain
            blockchain_service = BlockchainService()
            verification_result = blockchain_service.verify_document(
                user_id=request.user.id,
                document_id=record.document_id,
                document_hash=current_hash
            )
            
            # Log transaction
            BlockchainTransaction.objects.create(
                user=request.user,
                transaction_type='VERIFY',
                transaction_hash=verification_result['transaction_hash'],
                block_number=verification_result['block_number'],
                status='SUCCESS'
            )
            
            is_valid = verification_result['is_valid']
            
            return Response({
                'message': 'Verification complete',
                'is_valid': is_valid,
                'document_id': record.document_id,
                'stored_hash': record.document_hash,
                'current_hash': current_hash,
                'blockchain_verification': verification_result,
                'result': 'VERIFIED - Document is authentic and unchanged' if is_valid else 'FAILED - Document has been modified or corrupted'
            }, status=status.HTTP_200_OK)
        
        except MedicalRecord.DoesNotExist:
            return Response({
                'error': 'Medical record not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({
                'error': f'Verification failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== ADMIN VIEWS ====================

class PendingPatientsView(generics.ListAPIView):
    """Admin can view all pending patient registrations"""
    permission_classes = [IsAdmin]
    serializer_class = PatientListSerializer
    
    def get_queryset(self):
        return User.objects.filter(role='PATIENT', account_status='PENDING')


class ApproveRejectPatientView(APIView):
    """Admin can approve or reject patient registration"""
    permission_classes = [IsAdmin]
    
    def post(self, request, patient_id):
        serializer = PatientApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            patient = User.objects.get(id=patient_id, role='PATIENT')
            action = serializer.validated_data['action']
            
            if action == 'approve':
                patient.account_status = 'APPROVED'
                message = f'Patient {patient.email} has been approved'
            else:
                patient.account_status = 'REJECTED'
                message = f'Patient {patient.email} has been rejected'
            
            patient.save()
            
            return Response({
                'message': message,
                'patient': PatientListSerializer(patient).data
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({
                'error': 'Patient not found'
            }, status=status.HTTP_404_NOT_FOUND)


class SystemStatsView(APIView):
    """Admin can view system statistics"""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        stats = {
            'patients': {
                'total': User.objects.filter(role='PATIENT').count(),
                'pending': User.objects.filter(role='PATIENT', account_status='PENDING').count(),
                'approved': User.objects.filter(role='PATIENT', account_status='APPROVED').count(),
                'rejected': User.objects.filter(role='PATIENT', account_status='REJECTED').count(),
            },
            'it_staff': {
                'total': User.objects.filter(role='IT_STAFF').count(),
            },
            'medical_records': {
                'total': MedicalRecord.objects.count(),
                'confirmed': MedicalRecord.objects.filter(status='CONFIRMED').count(),
                'pending': MedicalRecord.objects.filter(status='PENDING').count(),
            },
            'blockchain_transactions': {
                'total': BlockchainTransaction.objects.count(),
                'registrations': BlockchainTransaction.objects.filter(transaction_type='REGISTER').count(),
                'verifications': BlockchainTransaction.objects.filter(transaction_type='VERIFY').count(),
            }
        }
        
        return Response(stats, status=status.HTTP_200_OK)