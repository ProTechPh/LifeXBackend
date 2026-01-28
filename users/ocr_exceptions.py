"""
OCR Exception Classes for Philippine ID Card Processing

Custom exceptions for handling OCR-related errors during
ID card verification and data extraction.
"""


class OCRError(Exception):
    """Base exception for OCR-related errors"""
    pass


class ImageQualityError(OCRError):
    """
    Raised when image quality is too poor for OCR processing.
    
    Common causes:
    - Image too blurry
    - Poor lighting
    - Low resolution
    - Excessive noise
    """
    pass


class IDTypeNotRecognizedError(OCRError):
    """
    Raised when the ID card type cannot be determined.
    
    This may occur when:
    - ID format is unknown
    - Image doesn't contain a valid Philippine ID
    - ID is from unsupported issuer
    """
    pass


class DataExtractionError(OCRError):
    """
    Raised when required data cannot be extracted from ID.
    
    This may occur when:
    - OCR confidence is too low
    - Required fields are missing
    - Text format doesn't match expected patterns
    - ID card is damaged or obscured
    """
    pass


class FaceExtractionError(OCRError):
    """
    Raised when face cannot be extracted from ID card.
    
    This may occur when:
    - No face detected in ID
    - Multiple faces detected
    - Face region is obscured
    - Face is too small or low quality
    """
    pass


class ValidationError(OCRError):
    """
    Raised when extracted data fails validation.
    
    This may occur when:
    - ID number format is invalid
    - Date format is incorrect
    - Required fields are empty
    - Data doesn't match expected patterns
    """
    pass
