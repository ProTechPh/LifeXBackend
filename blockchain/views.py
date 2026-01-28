from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from django.core.files.base import ContentFile

from .models import BlockchainDocument, BlockchainTransaction
from .serializers import (
    DocumentRegistrationSerializer,
    DocumentVerificationSerializer,
    BlockchainDocumentSerializer,
    BlockchainTransactionSerializer,
    DocumentDetailsSerializer
)
from .blockchain_service import BlockchainService
from .utils import (
    generate_document_id,
    hash_file,
    create_mock_pdf_data,
    verify_document_hash
)


class RegisterDocumentView(APIView):
    """
    Register a document hash on the blockchain
    
    FLOW:
    1. User uploads file or requests mock PDF
    2. System generates PDF (if mock)
    3. Hash the PDF
    4. Send hash to blockchain
    5. Save transaction details in database
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = DocumentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        document_type = serializer.validated_data['document_type']
        document_name = serializer.validated_data['document_name']
        file = serializer.validated_data.get('file')
        use_mock = serializer.validated_data.get('mock_data', True)
        
        try:
            # Generate unique document ID
            document_id = generate_document_id()
            
            # Create or use provided file
            if use_mock or not file:
                # Create mock PDF
                pdf_file = self._create_mock_pdf(user, document_type)
                file_to_hash = pdf_file
            else:
                file_to_hash = file
            
            # Hash the document
            document_hash = hash_file(file_to_hash)
            
            # Register on blockchain
            blockchain_service = BlockchainService()
            tx_result = blockchain_service.register_document(
                user_id=user.id,
                document_id=document_id,
                document_hash=document_hash,
                document_type=document_type
            )
            
            # Get user's blockchain address
            user_address = blockchain_service.get_account_for_user(user.id)
            
            # Save to database
            blockchain_doc = BlockchainDocument.objects.create(
                user=user,
                document_id=document_id,
                document_type=document_type,
                document_name=document_name,
                document_hash=document_hash,
                blockchain_address=user_address,
                transaction_hash=tx_result['transaction_hash'],
                block_number=tx_result['block_number'],
                status='CONFIRMED',
                registered_at=timezone.now()
            )
            
            # Save file if it was created
            if use_mock or not file:
                blockchain_doc.file.save(
                    f"{document_id}.pdf",
                    ContentFile(pdf_file.getvalue()),
                    save=True
                )
            elif file:
                blockchain_doc.file = file
                blockchain_doc.save()
            
            # Log transaction
            BlockchainTransaction.objects.create(
                user=user,
                transaction_type='REGISTER',
                transaction_hash=tx_result['transaction_hash'],
                block_number=tx_result['block_number'],
                gas_used=tx_result['gas_used'],
                document=blockchain_doc,
                status='SUCCESS'
            )
            
            return Response({
                'message': 'Document registered successfully on blockchain',
                'document': BlockchainDocumentSerializer(blockchain_doc).data,
                'blockchain_data': {
                    'transaction_hash': tx_result['transaction_hash'],
                    'block_number': tx_result['block_number'],
                    'gas_used': tx_result['gas_used'],
                    'blockchain_address': user_address
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'error': f'Failed to register document: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _create_mock_pdf(self, user, document_type):
        """
        Create a mock PDF document for testing
        """
        buffer = BytesIO()
        
        # Create PDF
        pdf = canvas.Canvas(buffer, pagesize=letter)
        
        # Get mock data
        mock_text = create_mock_pdf_data(user, document_type)
        
        # Add content to PDF
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(100, 750, "KYC Document")
        
        pdf.setFont("Helvetica", 12)
        y_position = 700
        for line in mock_text.strip().split('\n'):
            if line.strip():
                pdf.drawString(100, y_position, line.strip())
                y_position -= 20
        
        pdf.save()
        buffer.seek(0)
        
        return buffer


class VerifyDocumentView(APIView):
    """
    Verify if a document matches what's stored on blockchain
    
    FLOW:
    1. User uploads document to verify
    2. Hash the uploaded document
    3. Compare with hash stored on blockchain
    4. Return verification result
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = DocumentVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        document_id = serializer.validated_data['document_id']
        file = serializer.validated_data['file']
        
        try:
            # Get document from database
            blockchain_doc = BlockchainDocument.objects.get(
                document_id=document_id,
                user=user
            )
            
            # Hash the uploaded file
            uploaded_hash = hash_file(file)
            
            # Verify on blockchain
            blockchain_service = BlockchainService()
            verification_result = blockchain_service.verify_document(
                user_id=user.id,
                document_id=document_id,
                document_hash=uploaded_hash
            )
            
            # Log transaction
            BlockchainTransaction.objects.create(
                user=user,
                transaction_type='VERIFY',
                transaction_hash=verification_result['transaction_hash'],
                block_number=verification_result['block_number'],
                document=blockchain_doc,
                status='SUCCESS'
            )
            
            # Compare hashes
            is_valid = verification_result['is_valid']
            
            return Response({
                'message': 'Verification complete',
                'is_valid': is_valid,
                'document_id': document_id,
                'uploaded_hash': uploaded_hash,
                'stored_hash': blockchain_doc.document_hash,
                'blockchain_verification': verification_result,
                'result': 'MATCH - Document is authentic' if is_valid else 'MISMATCH - Document has been modified'
            }, status=status.HTTP_200_OK)
        
        except BlockchainDocument.DoesNotExist:
            return Response({
                'error': 'Document not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({
                'error': f'Verification failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetDocumentFromBlockchainView(APIView):
    """
    Retrieve document details directly from blockchain
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, document_id):
        user = request.user
        
        try:
            blockchain_service = BlockchainService()
            doc_data = blockchain_service.get_document(user.id, document_id)
            
            if not doc_data:
                return Response({
                    'error': 'Document not found on blockchain'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'message': 'Document retrieved from blockchain',
                'blockchain_data': DocumentDetailsSerializer(doc_data).data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': f'Failed to retrieve document: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserDocumentsView(generics.ListAPIView):
    """
    List all documents for the authenticated user
    """
    serializer_class = BlockchainDocumentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BlockchainDocument.objects.filter(user=self.request.user)


class UserTransactionsView(generics.ListAPIView):
    """
    List all blockchain transactions for the authenticated user
    """
    serializer_class = BlockchainTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BlockchainTransaction.objects.filter(user=self.request.user)


class BlockchainStatsView(APIView):
    """
    Get blockchain statistics for user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        try:
            blockchain_service = BlockchainService()
            
            # Get stats from blockchain
            doc_count = blockchain_service.get_document_count(user.id)
            user_address = blockchain_service.get_account_for_user(user.id)
            
            # Get stats from database
            db_doc_count = BlockchainDocument.objects.filter(user=user).count()
            db_tx_count = BlockchainTransaction.objects.filter(user=user).count()
            
            return Response({
                'user_email': user.email,
                'blockchain_address': user_address,
                'blockchain_stats': {
                    'documents_on_chain': doc_count,
                    'documents_in_database': db_doc_count,
                    'total_transactions': db_tx_count
                },
                'ganache_info': {
                    'network': 'Ganache (Local)',
                    'chain_id': 1337
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': f'Failed to get stats: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)