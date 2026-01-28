from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator


class MedicalRecord(models.Model):
    """
    Medical records uploaded by Nurses and viewable by patients
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
    
    APPROVAL_STATUS_CHOICES = (
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    # Patient this record belongs to
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medical_records',
        limit_choices_to={'role': 'PATIENT'}
    )
    
    # Nurse who uploaded this record
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_records',
        limit_choices_to={'role': 'NURSE'}
    )
    
    # Record information
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Medical details
    department = models.CharField(max_length=100, blank=True)
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
    document_hash = models.CharField(max_length=64)
    blockchain_address = models.CharField(max_length=42, blank=True)
    transaction_hash = models.CharField(max_length=66, blank=True)
    block_number = models.IntegerField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    is_verified = models.BooleanField(default=False)
    
    # External record approval workflow
    is_external = models.BooleanField(
        default=False,
        help_text='Whether this record was created externally'
    )
    
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='APPROVED',
        help_text='Approval status for external records'
    )
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_records',
        limit_choices_to={'role__in': ['NURSE', 'DOCTOR']}
    )
    
    approved_at = models.DateTimeField(null=True, blank=True)
    
    rejection_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    registered_on_blockchain_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Medical Record'
        verbose_name_plural = 'Medical Records'
        indexes = [
            models.Index(fields=['approval_status', 'is_external'], name='idx_approval_external'),
            models.Index(fields=['patient', 'created_at'], name='idx_patient_created'),
            models.Index(fields=['status'], name='idx_status'),
            models.Index(fields=['is_external', 'approval_status', 'created_at'], name='idx_external_approval_date'),
        ]
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


class BlockchainDocument(models.Model):
    """
    Django model to track blockchain transactions
    This stores metadata in our database while the actual hash lives on blockchain
    """
    
    DOCUMENT_TYPES = (
        ('KYC_ID', 'KYC Identity Document'),
        ('KYC_ADDRESS', 'KYC Address Proof'),
        ('KYC_PHOTO', 'KYC Photo'),
        ('OTHER', 'Other Document'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending Blockchain Confirmation'),
        ('CONFIRMED', 'Confirmed on Blockchain'),
        ('FAILED', 'Failed to Register'),
    )
    
    # Link to user
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blockchain_documents'
    )
    
    # Document information
    document_id = models.CharField(max_length=255, unique=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_name = models.CharField(max_length=255)
    
    # File reference (optional - for mock PDFs)
    file = models.FileField(upload_to='mock_pdfs/', blank=True, null=True)
    
    # Blockchain data
    document_hash = models.CharField(max_length=64)  # SHA-256 hash
    blockchain_address = models.CharField(max_length=42, blank=True)  # User's ETH address
    transaction_hash = models.CharField(max_length=66, blank=True)  # TX hash from blockchain
    block_number = models.IntegerField(null=True, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    registered_at = models.DateTimeField(null=True, blank=True)  # When registered on blockchain
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Blockchain Document'
        verbose_name_plural = 'Blockchain Documents'
    
    def __str__(self):
        return f"{self.document_type} - {self.user.email}"


class BlockchainTransaction(models.Model):
    """
    Track all blockchain transactions for auditing
    """
    
    TRANSACTION_TYPES = (
        ('REGISTER', 'Document Registration'),
        ('VERIFY', 'Document Verification'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blockchain_transactions'
    )
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    transaction_hash = models.CharField(max_length=66)
    block_number = models.IntegerField(null=True, blank=True)
    gas_used = models.IntegerField(null=True, blank=True)
    
    # Related document (if applicable)
    document = models.ForeignKey(
        BlockchainDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    
    # Additional data
    status = models.CharField(max_length=20, default='SUCCESS')
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Blockchain Transaction'
        verbose_name_plural = 'Blockchain Transactions'
    
    def __str__(self):
        return f"{self.transaction_type} - {self.transaction_hash[:10]}..."


class AuditLog(models.Model):
    """
    Track important user actions for security auditing
    """
    ACTION_CHOICES = (
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('REGISTER_PATIENT', 'Register Patient'),
        ('APPROVE_PATIENT', 'Approve Patient'),
        ('REJECT_PATIENT', 'Reject Patient'),
        ('UPLOAD_RECORD', 'Upload Medical Record'),
        ('VIEW_RECORDS', 'View Medical Records'),
        ('DOWNLOAD_RECORD', 'Download Medical Record'),
        ('VERIFY_RECORD', 'Verify Record on Blockchain'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50, blank=True)
    resource_id = models.CharField(max_length=50, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"