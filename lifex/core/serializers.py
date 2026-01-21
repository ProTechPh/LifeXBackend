from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PatientDocument

User = get_user_model()


class PatientDocumentSerializer(serializers.ModelSerializer):
    """Serializer for patient documents"""
    uploader_name = serializers.CharField(source='uploader.get_full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientDocument
        fields = (
            'id', 'patient', 'patient_name', 'uploader', 'uploader_name',
            'file', 'file_name', 'document_type', 'file_size', 'file_size_mb',
            'uploaded_at', 'updated_at'
        )
        read_only_fields = ('id', 'file_size', 'uploaded_at', 'updated_at', 'uploader')
    
    def get_file_size_mb(self, obj):
        return obj.get_file_size_mb()


class PatientListSerializer(serializers.ModelSerializer):
    """Serializer for listing patients"""
    full_name = serializers.CharField(source='get_full_name')
    document_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'date_joined', 'document_count')
    
    def get_document_count(self, obj):
        return obj.documents.count()