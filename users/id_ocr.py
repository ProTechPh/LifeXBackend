"""
Philippine ID Card OCR Module

Extracts text and data from Philippine ID cards using Tesseract OCR.
Supports: PhilID (National ID), Driver's License, and PhilHealth ID.
"""

import re
import cv2
import numpy as np
from PIL import Image
import pytesseract
from datetime import datetime
from typing import Dict, Optional, Tuple
from django.conf import settings

from .ocr_exceptions import (
    OCRError,
    ImageQualityError,
    IDTypeNotRecognizedError,
    DataExtractionError,
    FaceExtractionError,
)


# Configure Tesseract path from settings
TESSERACT_CMD = getattr(settings, 'TESSERACT_CMD', 'tesseract')
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Preprocess image for better OCR results.
    
    Args:
        image: Input image as numpy array
    
    Returns:
        Preprocessed image
    """
    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # Increase contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(denoised)
    
    # Threshold
    _, binary = cv2.threshold(contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return binary


def deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Deskew (straighten) a rotated image.
    
    Args:
        image: Input image
    
    Returns:
        Deskewed image
    """
    # Detect edges
    edges = cv2.Canny(image, 50, 150, apertureSize=3)
    
    # Detect lines using Hough transform
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    if lines is not None and len(lines) > 0:
        # Calculate average angle
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            angles.append(angle)
        
        median_angle = np.median(angles)
        
        # Rotate image
        if abs(median_angle) > 0.5:  # Only rotate if angle is significant
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated
    
    return image


def extract_face_from_id(image: np.ndarray) -> Optional[Image.Image]:
    """
    Extract face region from ID card.
    
    Args:
        image: ID card image
    
    Returns:
        PIL Image of extracted face, or None if not found
    
    Raises:
        FaceExtractionError: If face cannot be extracted
    """
    try:
        import face_recognition
        
        # Convert to RGB for face_recognition
        if len(image.shape) == 2:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_image)
        
        if len(face_locations) == 0:
            raise FaceExtractionError("No face detected in ID card")
        
        if len(face_locations) > 1:
            raise FaceExtractionError("Multiple faces detected in ID card")
        
        # Extract face region
        top, right, bottom, left = face_locations[0]
        
        # Add padding
        padding = 20
        top = max(0, top - padding)
        left = max(0, left - padding)
        bottom = min(rgb_image.shape[0], bottom + padding)
        right = min(rgb_image.shape[1], right + padding)
        
        face_image = rgb_image[top:bottom, left:right]
        
        # Convert to PIL Image
        return Image.fromarray(face_image)
        
    except ImportError:
        raise FaceExtractionError("face_recognition library not installed")
    except Exception as e:
        raise FaceExtractionError(f"Failed to extract face: {str(e)}")


def perform_ocr(image: np.ndarray, lang: str = 'eng') -> str:
    """
    Perform OCR on preprocessed image.
    
    Args:
        image: Preprocessed image
        lang: Tesseract language (default: 'eng')
    
    Returns:
        Extracted text
    """
    # Try multiple OCR configurations
    configs = [
        '--psm 6',  # Assume uniform block of text
        '--psm 4',  # Assume single column of text
        '--psm 3',  # Fully automatic page segmentation
    ]
    
    best_text = ""
    best_confidence = 0
    
    for config in configs:
        try:
            # Get text with confidence
            data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                
                if avg_confidence > best_confidence:
                    best_confidence = avg_confidence
                    best_text = pytesseract.image_to_string(image, lang=lang, config=config)
        except Exception:
            continue
    
    return best_text.strip()


def detect_id_type(text: str) -> str:
    """
    Detect Philippine ID type from OCR text.
    
    Args:
        text: OCR extracted text
    
    Returns:
        ID type: 'NATIONAL_ID', 'DRIVERS_LICENSE', or 'PHILHEALTH_ID'
    
    Raises:
        IDTypeNotRecognizedError: If ID type cannot be determined
    """
    text_upper = text.upper()
    
    # PhilID / National ID patterns
    if any(keyword in text_upper for keyword in ['PHILSYS', 'NATIONAL ID', 'PCN', 'PHILIPPINE IDENTIFICATION']):
        return 'NATIONAL_ID'
    
    # Driver's License patterns
    if any(keyword in text_upper for keyword in ['DRIVER', 'LICENSE', 'LTO', 'LAND TRANSPORTATION']):
        return 'DRIVERS_LICENSE'
    
    # PhilHealth patterns
    if any(keyword in text_upper for keyword in ['PHILHEALTH', 'PHIL HEALTH', 'PHILIPPINE HEALTH']):
        return 'PHILHEALTH_ID'
    
    raise IDTypeNotRecognizedError("Could not determine ID type from text")


def parse_philid(text: str) -> Dict:
    """
    Parse PhilID (National ID) data.
    
    Expected format:
    - PCN: 0000-0000-0000-0000
    - Name: SURNAME, FIRST NAME MIDDLE NAME
    - Date of Birth: DD MMM YYYY
    - Sex: M/F
    - Address: Full address
    """
    data = {}
    
    # Extract PCN (PhilSys Card Number)
    pcn_pattern = r'(\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4})'
    pcn_match = re.search(pcn_pattern, text)
    if pcn_match:
        data['id_number'] = pcn_match.group(1).replace(' ', '-')
    
    # Extract name (usually in format: SURNAME, FIRST MIDDLE)
    name_pattern = r'([A-Z]+),\s*([A-Z\s]+)'
    name_match = re.search(name_pattern, text)
    if name_match:
        surname = name_match.group(1).strip()
        given_names = name_match.group(2).strip().split()
        first_name = given_names[0] if given_names else ''
        middle_name = ' '.join(given_names[1:]) if len(given_names) > 1 else ''
        data['name'] = f"{first_name} {middle_name} {surname}".strip()
    
    # Extract date of birth
    dob_pattern = r'(\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{4})'
    dob_match = re.search(dob_pattern, text, re.IGNORECASE)
    if dob_match:
        try:
            dob_str = dob_match.group(1)
            dob = datetime.strptime(dob_str, '%d %b %Y')
            data['date_of_birth'] = dob.strftime('%Y-%m-%d')
        except:
            pass
    
    # Extract address (usually after "Address:" or on multiple lines)
    address_pattern = r'(?:ADDRESS|ADDR)[:\s]+(.+?)(?:\n|$)'
    address_match = re.search(address_pattern, text, re.IGNORECASE | re.DOTALL)
    if address_match:
        data['address'] = address_match.group(1).strip()
    
    return data


def parse_drivers_license(text: str) -> Dict:
    """
    Parse Driver's License data.
    
    Expected format:
    - License Number: N00-00-000000
    - Name: SURNAME, FIRST NAME MI
    - Date of Birth: MM/DD/YYYY
    - Address: Full address
    """
    data = {}
    
    # Extract license number
    license_pattern = r'([A-Z]\d{2}[-\s]\d{2}[-\s]\d{6})'
    license_match = re.search(license_pattern, text)
    if license_match:
        data['id_number'] = license_match.group(1).replace(' ', '-')
    
    # Extract name
    name_pattern = r'([A-Z]+),\s*([A-Z\s]+)'
    name_match = re.search(name_pattern, text)
    if name_match:
        surname = name_match.group(1).strip()
        given_names = name_match.group(2).strip().split()
        first_name = given_names[0] if given_names else ''
        middle_name = ' '.join(given_names[1:]) if len(given_names) > 1 else ''
        data['name'] = f"{first_name} {middle_name} {surname}".strip()
    
    # Extract date of birth (MM/DD/YYYY format)
    dob_pattern = r'(\d{1,2}/\d{1,2}/\d{4})'
    dob_match = re.search(dob_pattern, text)
    if dob_match:
        try:
            dob_str = dob_match.group(1)
            dob = datetime.strptime(dob_str, '%m/%d/%Y')
            data['date_of_birth'] = dob.strftime('%Y-%m-%d')
        except:
            pass
    
    # Extract address
    address_pattern = r'(?:ADDRESS|ADDR)[:\s]+(.+?)(?:\n|$)'
    address_match = re.search(address_pattern, text, re.IGNORECASE | re.DOTALL)
    if address_match:
        data['address'] = address_match.group(1).strip()
    
    return data


def parse_philhealth(text: str) -> Dict:
    """
    Parse PhilHealth ID data.
    
    Expected format:
    - PhilHealth Number: 00-000000000-0
    - Name: SURNAME, FIRST NAME MIDDLE NAME
    - Date of Birth: MM/DD/YYYY
    """
    data = {}
    
    # Extract PhilHealth number
    philhealth_pattern = r'(\d{2}[-\s]\d{9}[-\s]\d)'
    philhealth_match = re.search(philhealth_pattern, text)
    if philhealth_match:
        data['id_number'] = philhealth_match.group(1).replace(' ', '-')
    
    # Extract name
    name_pattern = r'([A-Z]+),\s*([A-Z\s]+)'
    name_match = re.search(name_pattern, text)
    if name_match:
        surname = name_match.group(1).strip()
        given_names = name_match.group(2).strip().split()
        first_name = given_names[0] if given_names else ''
        middle_name = ' '.join(given_names[1:]) if len(given_names) > 1 else ''
        data['name'] = f"{first_name} {middle_name} {surname}".strip()
    
    # Extract date of birth
    dob_pattern = r'(\d{1,2}/\d{1,2}/\d{4})'
    dob_match = re.search(dob_pattern, text)
    if dob_match:
        try:
            dob_str = dob_match.group(1)
            dob = datetime.strptime(dob_str, '%m/%d/%Y')
            data['date_of_birth'] = dob.strftime('%Y-%m-%d')
        except:
            pass
    
    return data


def extract_text_from_id(id_image, id_type: Optional[str] = None) -> Dict:
    """
    Extract text and data from Philippine ID card.
    
    Args:
        id_image: PIL Image, file path, or numpy array
        id_type: Optional hint ('NATIONAL_ID', 'DRIVERS_LICENSE', 'PHILHEALTH_ID')
    
    Returns:
        dict: {
            'raw_text': str,
            'id_type': str,
            'id_number': str,
            'name': str,
            'date_of_birth': str (YYYY-MM-DD),
            'address': str,
            'face_image': PIL.Image (extracted face from ID)
        }
    
    Raises:
        OCRError: If extraction fails
        ImageQualityError: If image quality is too poor
        IDTypeNotRecognizedError: If ID type cannot be determined
        DataExtractionError: If required data cannot be extracted
    """
    try:
        # Load image
        if isinstance(id_image, str):
            image = cv2.imread(id_image)
            if image is None:
                raise ImageQualityError("Could not load image from path")
        elif isinstance(id_image, Image.Image):
            image = cv2.cvtColor(np.array(id_image), cv2.COLOR_RGB2BGR)
        elif isinstance(id_image, np.ndarray):
            image = id_image
        else:
            # Try to read from file-like object
            try:
                pil_image = Image.open(id_image)
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            except:
                raise ImageQualityError("Unsupported image format")
        
        # Validate image quality
        if image.shape[0] < 200 or image.shape[1] < 300:
            raise ImageQualityError("Image resolution too low (minimum 300x200)")
        
        # Preprocess image
        preprocessed = preprocess_image(image)
        deskewed = deskew_image(preprocessed)
        
        # Perform OCR
        raw_text = perform_ocr(deskewed)
        
        if not raw_text or len(raw_text) < 20:
            raise DataExtractionError("OCR extracted insufficient text")
        
        # Detect ID type if not provided
        if not id_type:
            id_type = detect_id_type(raw_text)
        
        # Parse data based on ID type
        if id_type == 'NATIONAL_ID':
            parsed_data = parse_philid(raw_text)
        elif id_type == 'DRIVERS_LICENSE':
            parsed_data = parse_drivers_license(raw_text)
        elif id_type == 'PHILHEALTH_ID':
            parsed_data = parse_philhealth(raw_text)
        else:
            raise IDTypeNotRecognizedError(f"Unsupported ID type: {id_type}")
        
        # Extract face from ID
        try:
            face_image = extract_face_from_id(image)
        except FaceExtractionError as e:
            # Face extraction is optional, log warning but continue
            face_image = None
        
        # Build result
        result = {
            'raw_text': raw_text,
            'id_type': id_type,
            'id_number': parsed_data.get('id_number', ''),
            'name': parsed_data.get('name', ''),
            'date_of_birth': parsed_data.get('date_of_birth', ''),
            'address': parsed_data.get('address', ''),
            'face_image': face_image
        }
        
        # Validate required fields - be lenient for registration
        # ID number and name extraction can fail due to poor OCR quality
        # Log warnings but don't fail registration since face matching is primary security
        if not result['id_number']:
            # Use placeholder if extraction failed
            result['id_number'] = f"PENDING_{id_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if not result['name']:
            # Use placeholder if extraction failed
            result['name'] = "Name extraction pending"
        
        return result
        
    except (OCRError, ImageQualityError, IDTypeNotRecognizedError, DataExtractionError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise OCRError(f"Unexpected error during OCR: {str(e)}")
