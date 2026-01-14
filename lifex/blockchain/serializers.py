from rest_framework import serializers
from .models import BlockchainDocument, BlockchainTransaction


class DocumentRegistrationSerializer(serializers.Serializer):
    """
    Serializer for registering a new document on blockchain
    """
    document_type = serializers.ChoiceField(
        choices=['KYC_ID', 'KYC_ADDRESS', 'KYC_PHOTO', 'OTHER'],
        required=True
    )
    document_name = serializers.CharField(max_length=255, required=True)
    file = serializers.FileField(required=False, allow_null=True)
    
    # If no file provided, we'll create mock data
    mock_data = serializers.BooleanField(default=True, required=False)


class DocumentVerificationSerializer(serializers.Serializer):
    """
    Serializer for verifying a document
    """
    document_id = serializers.CharField(max_length=255, required=True)
    file = serializers.FileField(required=True)


class BlockchainDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for BlockchainDocument model
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    short_hash = serializers.SerializerMethodField()
    short_tx_hash = serializers.SerializerMethodField()
    
    class Meta:
        model = BlockchainDocument
        fields = (
            'id',
            'user_email',
            'document_id',
            'document_type',
            'document_name',
            'document_hash',
            'short_hash',
            'blockchain_address',
            'transaction_hash',
            'short_tx_hash',
            'block_number',
            'status',
            'created_at',
            'registered_at'
        )
        read_only_fields = (
            'id',
            'document_hash',
            'blockchain_address',
            'transaction_hash',
            'block_number',
            'status',
            'created_at',
            'registered_at'
        )
    
    def get_short_hash(self, obj):
        """Return shortened hash for display"""
        if obj.document_hash:
            return f"{obj.document_hash[:8]}...{obj.document_hash[-8:]}"
        return None
    
    def get_short_tx_hash(self, obj):
        """Return shortened transaction hash for display"""
        if obj.transaction_hash:
            return f"{obj.transaction_hash[:10]}...{obj.transaction_hash[-8:]}"
        return None


class BlockchainTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for BlockchainTransaction model
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    short_tx_hash = serializers.SerializerMethodField()
    
    class Meta:
        model = BlockchainTransaction
        fields = (
            'id',
            'user_email',
            'transaction_type',
            'transaction_hash',
            'short_tx_hash',
            'block_number',
            'gas_used',
            'status',
            'error_message',
            'created_at'
        )
        read_only_fields = '__all__'
    
    def get_short_tx_hash(self, obj):
        """Return shortened transaction hash for display"""
        if obj.transaction_hash:
            return f"{obj.transaction_hash[:10]}...{obj.transaction_hash[-8:]}"
        return None


class DocumentDetailsSerializer(serializers.Serializer):
    """
    Serializer for document details from blockchain
    """
    document_hash = serializers.CharField()
    owner = serializers.CharField()
    timestamp = serializers.IntegerField()
    document_type = serializers.CharField()
    exists = serializers.BooleanField()
    
    # Add human-readable fields
    formatted_timestamp = serializers.SerializerMethodField()
    short_hash = serializers.SerializerMethodField()
    
    def get_formatted_timestamp(self, obj):
        """Convert Unix timestamp to readable format"""
        from datetime import datetime
        return datetime.fromtimestamp(obj['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
    
    def get_short_hash(self, obj):
        """Return shortened hash for display"""
        hash_val = obj['document_hash']
        if hash_val:
            return f"{hash_val[:8]}...{hash_val[-8:]}"
        return None