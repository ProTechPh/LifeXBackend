"""
Blockchain integration utilities for biometric data.

Handles:
- Generating unique biometric IDs
- Hashing biometric data (ID card + face encodings)
- Registering biometric data on blockchain
- Verifying biometric data against blockchain
"""

import hashlib
import uuid
import json
from datetime import datetime
from django.core.files.base import ContentFile
from blockchain.blockchain_service import BlockchainService
from blockchain.models import AuditLog


def generate_biometric_id():
    """
    Generate unique biometric ID.
    Format: BIO_YYYYMMDD_UUID
    """
    timestamp = datetime.now().strftime('%Y%m%d')
    unique_id = str(uuid.uuid4())[:8]
    return f"BIO_{timestamp}_{unique_id}"


def hash_biometric_data(id_card_file, live_face_file, id_face_encoding, live_face_encoding):
    """
    Generate SHA-256 hash of combined biometric data.
    
    Combines:
    - ID card image hash
    - Live face image hash
    - ID face encoding (if available)
    - Live face encoding
    
    This creates a unique fingerprint of all biometric data.
    """
    sha256_hash = hashlib.sha256()
    
    # Hash ID card image
    id_card_file.seek(0)
    for chunk in iter(lambda: id_card_file.read(4096), b""):
        sha256_hash.update(chunk)
    
    # Hash live face image
    live_face_file.seek(0)
    for chunk in iter(lambda: live_face_file.read(4096), b""):
        sha256_hash.update(chunk)
    
    # Hash ID face encoding if available
    if id_face_encoding:
        encoding_str = json.dumps(id_face_encoding, sort_keys=True)
        sha256_hash.update(encoding_str.encode('utf-8'))
    
    # Hash live face encoding
    encoding_str = json.dumps(live_face_encoding, sort_keys=True)
    sha256_hash.update(encoding_str.encode('utf-8'))
    
    # Reset file pointers
    id_card_file.seek(0)
    live_face_file.seek(0)
    
    return sha256_hash.hexdigest()


def register_biometric_on_blockchain(user, biometric_data):
    """
    Register biometric data on blockchain.
    
    Args:
        user: User instance
        biometric_data: BiometricData instance
        
    Returns:
        dict: Transaction result with transaction_hash, block_number, status
        
    Raises:
        Exception: If blockchain registration fails
    """
    try:
        # Initialize blockchain service
        blockchain_service = BlockchainService()
        
        # Register on blockchain
        result = blockchain_service.register_document(
            user_id=user.id,
            document_id=biometric_data.biometric_id,
            document_hash=biometric_data.biometric_hash,
            document_type='BIOMETRIC_DATA'
        )
        
        # Update biometric data with blockchain info
        biometric_data.blockchain_address = blockchain_service.get_account_for_user(user.id)
        biometric_data.transaction_hash = result['transaction_hash']
        biometric_data.block_number = result['block_number']
        biometric_data.status = 'CONFIRMED' if result['status'] == 'success' else 'FAILED'
        biometric_data.is_blockchain_verified = (result['status'] == 'success')
        biometric_data.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=user,
            action='BIOMETRIC_BLOCKCHAIN_REGISTRATION',
            resource_type='BiometricData',
            resource_id=str(biometric_data.id),
            details=f"Biometric data registered on blockchain. TX: {result['transaction_hash']}, Block: {result['block_number']}"
        )
        
        return result
        
    except Exception as e:
        # Mark as failed
        biometric_data.status = 'FAILED'
        biometric_data.save()
        
        # Log the failure
        AuditLog.objects.create(
            user=user,
            action='BIOMETRIC_BLOCKCHAIN_REGISTRATION_FAILED',
            resource_type='BiometricData',
            resource_id=str(biometric_data.id),
            details=f"Failed to register biometric data on blockchain: {str(e)}"
        )
        
        raise Exception(f"Blockchain registration failed: {str(e)}")


def verify_biometric_on_blockchain(user, biometric_data):
    """
    Verify biometric data against blockchain.
    
    Args:
        user: User instance
        biometric_data: BiometricData instance
        
    Returns:
        dict: Verification result with is_valid, transaction_hash, block_number
    """
    try:
        # Initialize blockchain service
        blockchain_service = BlockchainService()
        
        # Verify on blockchain
        result = blockchain_service.verify_document(
            user_id=user.id,
            document_id=biometric_data.biometric_id,
            document_hash=biometric_data.biometric_hash
        )
        
        # Update verification status
        biometric_data.is_blockchain_verified = result['is_valid']
        biometric_data.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=user,
            action='BIOMETRIC_BLOCKCHAIN_VERIFICATION',
            resource_type='BiometricData',
            resource_id=str(biometric_data.id),
            details=f"Biometric data verification: {'VALID' if result['is_valid'] else 'INVALID'}"
        )
        
        return result
        
    except Exception as e:
        # Log the failure
        AuditLog.objects.create(
            user=user,
            action='BIOMETRIC_BLOCKCHAIN_VERIFICATION_FAILED',
            resource_type='BiometricData',
            resource_id=str(biometric_data.id),
            details=f"Failed to verify biometric data on blockchain: {str(e)}"
        )
        
        raise Exception(f"Blockchain verification failed: {str(e)}")


def get_biometric_blockchain_status(biometric_data):
    """
    Get blockchain status for biometric data.
    
    Returns:
        dict: Status information including transaction details
    """
    return {
        'biometric_id': biometric_data.biometric_id,
        'status': biometric_data.status,
        'is_verified': biometric_data.is_blockchain_verified,
        'blockchain_address': biometric_data.blockchain_address,
        'transaction_hash': biometric_data.transaction_hash,
        'block_number': biometric_data.block_number,
        'biometric_hash': biometric_data.biometric_hash,
    }
