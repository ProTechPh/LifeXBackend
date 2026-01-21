from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import PatientDocument
from .serializers import PatientDocumentSerializer, PatientListSerializer
from users.permissions import IsAdmin, IsITStaff, IsPatient

User = get_user_model()

# Constants
MAX_TOTAL_FILE_SIZE = 100 * 1024 * 1024  # 100MB in bytes
ALLOWED_EXTENSIONS = {
    'PDF': ['.pdf'],
    'IMAGE': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
    'DOCUMENT': ['.xlsx', '.xls', '.docx', '.doc', '.txt', '.csv']
}


class PatientListView(generics.ListAPIView):
    """
    List all patients (IT_STAFF and ADMIN only)
    """
    serializer_class = PatientListSerializer
    permission_classes = [permissions.IsAuthenticated, IsITStaff]
    
    def get_queryset(self):
        # Only show patients
        return User.objects.filter(role='PATIENT')


class PatientDocumentUploadView(APIView):
    """
    Handle file uploads for patients (IT_STAFF only)
    """
    permission_classes = [permissions.IsAuthenticated, IsITStaff]
    
    def post(self, request, patient_id):
        """Upload document for a patient"""
        
        # Verify patient exists
        try:
            patient = User.objects.get(id=patient_id, role='PATIENT')
        except User.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate file upload
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        document_type = request.data.get('document_type')
        
        if not document_type:
            return Response(
                {'error': 'Document type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if document_type not in dict(PatientDocument.DOCUMENT_TYPE_CHOICES):
            return Response(
                {'error': f'Invalid document type. Choose from: {", ".join(dict(PatientDocument.DOCUMENT_TYPE_CHOICES).keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size
        file_size = file.size
        if file_size > MAX_TOTAL_FILE_SIZE:
            return Response(
                {'error': f'File size exceeds maximum limit of 100MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check total patient storage
        total_patient_size = sum(doc.file_size for doc in patient.documents.all())
        if total_patient_size + file_size > MAX_TOTAL_FILE_SIZE:
            remaining = MAX_TOTAL_FILE_SIZE - total_patient_size
            return Response(
                {'error': f'Patient storage limit exceeded. Only {remaining / (1024 * 1024):.2f}MB remaining'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file extension
        file_name = file.name
        file_extension = file_name.lower().split('.')[-1]
        allowed_extensions = [ext.lstrip('.') for ext in ALLOWED_EXTENSIONS.get(document_type, [])]
        
        if file_extension not in allowed_extensions:
            return Response(
                {'error': f'Invalid file type for {document_type}. Allowed: {", ".join(allowed_extensions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create document record
        try:
            document = PatientDocument.objects.create(
                patient=patient,
                uploader=request.user,
                file=file,
                file_name=file_name,
                document_type=document_type,
                file_size=file_size
            )
            
            return Response(
                {
                    'message': 'Document uploaded successfully',
                    'document': PatientDocumentSerializer(document).data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PatientDocumentListView(generics.ListAPIView):
    """
    List documents for a patient
    - Patients see only their own documents
    - IT_STAFF can see any patient's documents
    - Admin can see all documents
    """
    serializer_class = PatientDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        patient_id = self.kwargs.get('patient_id')
        
        # Admin sees all documents
        if user.role == 'ADMIN':
            if patient_id:
                return PatientDocument.objects.filter(patient_id=patient_id)
            return PatientDocument.objects.all()
        
        # IT_STAFF can view any patient's documents
        if user.role == 'IT_STAFF':
            if patient_id:
                return PatientDocument.objects.filter(patient_id=patient_id)
            return PatientDocument.objects.all()
        
        # Patients only see their own documents
        if user.role == 'PATIENT':
            if patient_id:
                # Patient trying to view another patient's documents
                if int(patient_id) != user.id:
                    return PatientDocument.objects.none()
            return PatientDocument.objects.filter(patient=user)
        
        return PatientDocument.objects.none()


class PatientDocumentDetailView(generics.RetrieveDestroyAPIView):
    """
    Retrieve or delete a specific document
    Only IT_STAFF and ADMIN can delete; Patients can only view
    """
    serializer_class = PatientDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin and IT_STAFF see all
        if user.role in ['ADMIN', 'IT_STAFF']:
            return PatientDocument.objects.all()
        
        # Patients see only their own
        return PatientDocument.objects.filter(patient=user)
    
    def delete(self, request, *args, **kwargs):
        """Only IT_STAFF and ADMIN can delete documents"""
        user = request.user
        
        if user.role not in ['IT_STAFF', 'ADMIN']:
            return Response(
                {'error': 'You do not have permission to delete documents'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().delete(request, *args, **kwargs)