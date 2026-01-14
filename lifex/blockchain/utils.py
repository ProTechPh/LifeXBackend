import hashlib
import uuid
from datetime import datetime
from PyPDF2 import PdfReader
from io import BytesIO


def generate_document_id():
    """
    Generate unique document ID
    Format: DOC_YYYYMMDD_UUID
    """
    timestamp = datetime.now().strftime('%Y%m%d')
    unique_id = str(uuid.uuid4())[:8]
    return f"DOC_{timestamp}_{unique_id}"


def hash_file(file):
    """
    Generate SHA-256 hash of a file
    
    WHAT IS HASHING?
    - Takes any data (file, text, etc.) and creates a unique "fingerprint"
    - Same file = Same hash (always)
    - Different file = Different hash
    - Cannot reverse the hash to get original file
    - Even tiny change in file creates completely different hash
    
    Example:
    File A: "Hello World" → Hash: "a591a6d40bf420..."
    File B: "Hello World" → Hash: "a591a6d40bf420..." (same!)
    File C: "Hello World!" → Hash: "c0535e4be2b79f..." (different!)
    """
    
    # Create SHA-256 hasher
    sha256_hash = hashlib.sha256()
    
    # Read file in chunks (memory efficient for large files)
    file.seek(0)  # Reset file pointer to beginning
    for chunk in iter(lambda: file.read(4096), b""):
        sha256_hash.update(chunk)
    
    # Return hexadecimal hash string
    return sha256_hash.hexdigest()


def hash_text(text):
    """
    Generate SHA-256 hash of text string
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def extract_pdf_text(pdf_file):
    """
    Extract text from PDF file
    This is useful for reading mock PDFs
    """
    try:
        pdf_file.seek(0)  # Reset file pointer
        
        # Read PDF
        pdf_reader = PdfReader(pdf_file)
        
        # Extract text from all pages
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        return text.strip()
    
    except Exception as e:
        return f"Error reading PDF: {str(e)}"


def create_mock_pdf_data(user, document_type='KYC_ID'):
    """
    Create mock KYC data for PDF
    This simulates what real KYC documents would contain
    """
    
    mock_data = {
        'KYC_ID': f"""
        IDENTITY DOCUMENT
        
        Full Name: {user.get_full_name() or 'User'}
        Email: {user.email}
        Document Type: Government ID
        Issue Date: 2024-01-01
        Expiry Date: 2029-01-01
        Document Number: ID{user.id:08d}
        
        This is a mock document for testing purposes.
        """,
        
        'KYC_ADDRESS': f"""
        ADDRESS PROOF DOCUMENT
        
        Full Name: {user.get_full_name() or 'User'}
        Email: {user.email}
        Address: 123 Test Street, Test City
        Document Type: Utility Bill
        Date: 2024-01-01
        Account Number: ACC{user.id:08d}
        
        This is a mock document for testing purposes.
        """,
        
        'KYC_PHOTO': f"""
        PHOTOGRAPH DOCUMENT
        
        Full Name: {user.get_full_name() or 'User'}
        Email: {user.email}
        Photo Type: Passport Photo
        Date Taken: 2024-01-01
        Photo ID: PHOTO{user.id:08d}
        
        This is a mock document for testing purposes.
        """,
    }
    
    return mock_data.get(document_type, mock_data['KYC_ID'])


def verify_document_hash(original_hash, new_file):
    """
    Verify if a file matches the stored hash
    Returns True if hashes match, False otherwise
    """
    new_hash = hash_file(new_file)
    return original_hash == new_hash


def format_ethereum_address(address):
    """
    Format Ethereum address with checksum
    """
    if address.startswith('0x'):
        return address
    return f"0x{address}"


def shorten_hash(hash_string, length=8):
    """
    Shorten hash for display purposes
    Example: "a591a6d40bf420..." → "a591a6d4...bf420"
    """
    if len(hash_string) <= length * 2:
        return hash_string
    return f"{hash_string[:length]}...{hash_string[-length:]}"