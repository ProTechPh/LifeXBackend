from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import MedicalRecord

User = get_user_model()


class PatientRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for IT Staff to register new patients"""
    password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('email', 'password', 'first_name', 'last_name')
    
    def create(self, validated_data):
        """Create patient with PENDING status"""
        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            role='PATIENT',
            account_status='PENDING',
            **validated_data
        )
        return user


class PatientListSerializer(serializers.ModelSerializer):
    """Serializer for listing patients"""
    full_name = serializers.SerializerMethodField()
    records_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'account_status',
            'kyc_status',
            'date_joined',
            'records_count'
        )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_records_count(self, obj):
        return obj.medical_records.count()


class MedicalRecordUploadSerializer(serializers.ModelSerializer):
    """Serializer for IT Staff to upload medical records"""
    patient_email = serializers.EmailField(write_only=True)
    
    class Meta:
        model = MedicalRecord
        fields = (
            'patient_email',
            'record_type',
            'title',
            'description',
            'department',
            'date_of_service',
            'document_file'
        )
    
    def validate_patient_email(self, value):
        """Validate that patient exists and is approved"""
        try:
            patient = User.objects.get(email=value, role='PATIENT')
            if patient.account_status != 'APPROVED':
                raise serializers.ValidationError(
                    "Patient account is not approved yet."
                )
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Patient with this email does not exist."
            )
    
    def validate_document_file(self, value):
        """Validate file size (max 25MB)"""
        max_size = 25 * 1024 * 1024  # 25MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size cannot exceed 25MB. Current size: {value.size / (1024*1024):.2f}MB"
            )
        return value


class MedicalRecordSerializer(serializers.ModelSerializer):
    """Serializer for viewing medical records"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    patient_email = serializers.EmailField(source='patient.email', read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    file_extension = serializers.CharField(source='get_file_extension', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    short_hash = serializers.SerializerMethodField()
    short_tx_hash = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalRecord
        fields = (
            'id',
            'patient_name',
            'patient_email',
            'uploaded_by_name',
            'record_type',
            'title',
            'description',
            'department',
            'date_of_service',
            'file_url',
            'file_extension',
            'file_size_mb',
            'document_id',
            'document_hash',
            'short_hash',
            'blockchain_address',
            'transaction_hash',
            'short_tx_hash',
            'block_number',
            'status',
            'is_verified',
            'created_at',
            'registered_on_blockchain_at'
        )
    
    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.email
        return "Unknown"
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.document_file and request:
            return request.build_absolute_uri(obj.document_file.url)
        return None
    
    def get_file_size_mb(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024*1024):.2f} MB"
        return None
    
    def get_short_hash(self, obj):
        if obj.document_hash:
            return f"{obj.document_hash[:8]}...{obj.document_hash[-8:]}"
        return None
    
    def get_short_tx_hash(self, obj):
        if obj.transaction_hash:
            return f"{obj.transaction_hash[:10]}...{obj.transaction_hash[-8:]}"
        return None


class PatientApprovalSerializer(serializers.Serializer):
    """Serializer for approving/rejecting patients"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(required=False, allow_blank=True)