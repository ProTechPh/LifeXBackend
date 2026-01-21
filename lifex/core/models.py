from django.db import models
from django.contrib.auth import get_user_model
import os

User = get_user_model()


class PatientDocument(models.Model):
    """Model for storing patient medical documents/files"""
    
    DOCUMENT_TYPE_CHOICES = (
        ('PDF', 'PDF Document'),
        ('IMAGE', 'Image File'),
        ('DOCUMENT', 'Document File (Excel, Word, etc)'),
    )
    
    # Relationships
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='documents',
        limit_choices_to={'role': 'PATIENT'}
    )
    uploader = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
        limit_choices_to={'role': 'IT_STAFF'}
    )
    
    # Document details
    file = models.FileField(upload_to='patient_docs/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    file_size = models.BigIntegerField(help_text="File size in bytes")
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Patient Document'
        verbose_name_plural = 'Patient Documents'
    
    def __str__(self):
        return f"{self.file_name} - {self.patient.get_full_name()}"
    
    def get_file_size_mb(self):
        """Return file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    def get_file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.file_name)[1].lower()