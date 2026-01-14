from django.urls import path
from .views import (
    RegisterDocumentView,
    VerifyDocumentView,
    GetDocumentFromBlockchainView,
    UserDocumentsView,
    UserTransactionsView,
    BlockchainStatsView,
)

app_name = 'blockchain'

urlpatterns = [
    # Document operations
    path('register/', RegisterDocumentView.as_view(), name='register_document'),
    path('verify/', VerifyDocumentView.as_view(), name='verify_document'),
    path('document/<str:document_id>/', GetDocumentFromBlockchainView.as_view(), name='get_document'),
    
    # User data
    path('my-documents/', UserDocumentsView.as_view(), name='user_documents'),
    path('my-transactions/', UserTransactionsView.as_view(), name='user_transactions'),
    path('stats/', BlockchainStatsView.as_view(), name='blockchain_stats'),
]