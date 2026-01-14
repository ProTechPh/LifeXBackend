from django.contrib import admin
from .models import BlockchainDocument, BlockchainTransaction


@admin.register(BlockchainDocument)
class BlockchainDocumentAdmin(admin.ModelAdmin):
    """Admin interface for BlockchainDocument"""
    
    list_display = (
        'document_id',
        'user',
        'document_type',
        'document_name',
        'status',
        'block_number',
        'created_at'
    )
    
    list_filter = ('document_type', 'status', 'created_at')
    search_fields = ('document_id', 'user__email', 'transaction_hash')
    readonly_fields = (
        'document_id',
        'document_hash',
        'blockchain_address',
        'transaction_hash',
        'block_number',
        'created_at',
        'registered_at'
    )
    
    fieldsets = (
        ('Document Info', {
            'fields': ('user', 'document_id', 'document_type', 'document_name', 'file')
        }),
        ('Blockchain Data', {
            'fields': (
                'document_hash',
                'blockchain_address',
                'transaction_hash',
                'block_number',
                'status'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'registered_at')
        }),
    )


@admin.register(BlockchainTransaction)
class BlockchainTransactionAdmin(admin.ModelAdmin):
    """Admin interface for BlockchainTransaction"""
    
    list_display = (
        'id',
        'user',
        'transaction_type',
        'short_tx_hash',
        'block_number',
        'gas_used',
        'status',
        'created_at'
    )
    
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('transaction_hash', 'user__email')
    readonly_fields = (
        'user',
        'transaction_type',
        'transaction_hash',
        'block_number',
        'gas_used',
        'document',
        'status',
        'error_message',
        'created_at'
    )
    
    def short_tx_hash(self, obj):
        """Display shortened transaction hash"""
        if obj.transaction_hash:
            return f"{obj.transaction_hash[:10]}...{obj.transaction_hash[-8:]}"
        return '-'
    
    short_tx_hash.short_description = 'TX Hash'