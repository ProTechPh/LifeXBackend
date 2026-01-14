from django.db import models
from django.conf import settings

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