from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator

class MedicalRecord(models.Model):
    """
    Medical records uploaded by IT Staff and viewable by patients
    All files are hashed and stored on blockchain for verification
    """
    
    RECORD_TYPE_CHOICES = (
        ('LAB_RESULT', 'Laboratory Result'),
        ('XRAY', 'X-Ray Report'),
        ('CT_SCAN', 'CT Scan'),
        ('MRI', 'MRI Scan'),
        ('PRESCRIPTION', 'Prescription'),
        ('CONSULTATION', 'Consultation Notes'),
        ('DIAGNOSIS', 'Diagnosis Report'),
        ('VACCINATION', 'Vaccination Record'),
        ('OTHER', 'Other Medical Document'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending Blockchain Confirmation'),
        ('CONFIRMED', 'Confirmed on Blockchain'),
        ('FAILED', 'Failed to Register'),
    )
    
    # Patient this record belongs to
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medical_records',
        limit_choices_to={'role': 'PATIENT'}
    )
    
    # IT Staff who uploaded this record
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_records',
        limit_choices_to={'role': 'IT_STAFF'}
    )
    
    # Record information
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Medical details
    department = models.CharField(max_length=100, blank=True)  # e.g., Radiology, Lab, etc.
    date_of_service = models.DateField(help_text="Date when the medical service was provided")
    
    # File storage
    document_file = models.FileField(
        upload_to='medical_records/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx']
            )
        ]
    )
    file_size = models.IntegerField(help_text="File size in bytes", null=True, blank=True)
    
    # Blockchain data
    document_id = models.CharField(max_length=255, unique=True)
    document_hash = models.CharField(max_length=64)  # SHA-256 hash
    blockchain_address = models.CharField(max_length=42, blank=True)
    transaction_hash = models.CharField(max_length=66, blank=True)
    block_number = models.IntegerField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    is_verified = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    registered_on_blockchain_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date_of_service', '-created_at']
        verbose_name = 'Medical Record'
        verbose_name_plural = 'Medical Records'
        indexes = [
            models.Index(fields=['patient', 'date_of_service']),
            models.Index(fields=['document_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.record_type} - {self.patient.email} - {self.date_of_service}"
    
    def get_file_extension(self):
        """Get file extension"""
        return self.document_file.name.split('.')[-1].upper()
    
    def save(self, *args, **kwargs):
        """Override save to calculate file size"""
        if self.document_file:
            self.file_size = self.document_file.size
        super().save(*args, **kwargs)