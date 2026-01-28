"""
Biometric utility functions for face recognition.

This module provides core functionality for:
- Face detection and extraction from images
- Face encoding generation for recognition
- Face comparison and matching
- Image preprocessing and quality validation
- Liveness detection for anti-spoofing

Note: ID card OCR is now handled by Didit.me integration.
      See users/didit_service.py for ID verification.
"""

import os
import io
import base64
from PIL import Image
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from typing import Tuple, Optional, Dict, List, Union

# Try to import biometric libraries - make them optional
try:
    import cv2
    import numpy as np
    import face_recognition
    BIOMETRIC_AVAILABLE = True
except ImportError as e:
    BIOMETRIC_AVAILABLE = False
    print(f"WARNING: Biometric libraries not available: {e}")
    print("Biometric features will be disabled. Install with: pip install opencv-python face-recognition")
    # Create dummy numpy for type hints
    import sys
    from unittest.mock import MagicMock
    sys.modules['numpy'] = MagicMock()
    import numpy as np


class BiometricError(Exception):
    """Base exception for biometric processing errors"""
    pass


class FaceDetectionError(BiometricError):
    """Raised when face detection fails"""
    pass


class FaceQualityError(BiometricError):
    """Raised when face image quality is insufficient"""
    pass


class LivenessError(BiometricError):
    """Raised when liveness detection fails"""
    pass


def load_image_from_file(image_file) -> np.ndarray:
    """
    Load an image from a file or uploaded file object.
    
    Args:
        image_file: File path, Django UploadedFile, or file-like object
        
    Returns:
        numpy.ndarray: Image in RGB format
        
    Raises:
        BiometricError: If image cannot be loaded
    """
    if not BIOMETRIC_AVAILABLE:
        raise BiometricError("Biometric features are not available. Please install required libraries.")
    
    try:
        if isinstance(image_file, str):
            # File path
            image = face_recognition.load_image_file(image_file)
        elif isinstance(image_file, InMemoryUploadedFile):
            # Django uploaded file
            image = face_recognition.load_image_file(image_file)
        else:
            # File-like object
            image = face_recognition.load_image_file(image_file)
        
        return image
    except Exception as e:
        raise BiometricError(f"Failed to load image: {str(e)}")


def detect_and_extract_face(image_file, padding_percent: float = 0.15) -> Tuple[Optional[np.ndarray], Optional[Tuple]]:
    """
    Detect and extract face from an image with padding for better recognition.
    
    Args:
        image_file: Image file containing a face
        padding_percent: Percentage of face size to add as padding (default: 15%)
        
    Returns:
        tuple: (face_image, face_location)
            - face_image: Cropped face image as numpy array (with padding)
            - face_location: Tuple of (top, right, bottom, left) of padded region
            
    Raises:
        FaceDetectionError: If no face or multiple faces detected
    """
    if not BIOMETRIC_AVAILABLE:
        raise FaceDetectionError("Biometric features are not available. Please install required libraries.")
    
    try:
        # Load image
        image = load_image_from_file(image_file)
        
        # Detect faces
        face_locations = face_recognition.face_locations(image)
        
        if len(face_locations) == 0:
            raise FaceDetectionError("No face detected in image")
        
        if len(face_locations) > 1:
            raise FaceDetectionError(f"Multiple faces detected ({len(face_locations)}). Please ensure only one face is visible.")
        
        # Extract face region with padding
        top, right, bottom, left = face_locations[0]
        
        # Calculate padding based on face size
        face_height = bottom - top
        face_width = right - left
        padding_y = int(face_height * padding_percent)
        padding_x = int(face_width * padding_percent)
        
        # Apply padding with boundary checks
        padded_top = max(0, top - padding_y)
        padded_bottom = min(image.shape[0], bottom + padding_y)
        padded_left = max(0, left - padding_x)
        padded_right = min(image.shape[1], right + padding_x)
        
        # Extract padded face
        face_image = image[padded_top:padded_bottom, padded_left:padded_right]
        
        return face_image, (padded_top, padded_right, padded_bottom, padded_left)
        
    except FaceDetectionError:
        raise
    except Exception as e:
        raise FaceDetectionError(f"Face detection failed: {str(e)}")


def generate_face_encoding(image_file) -> np.ndarray:
    """
    Generate 128-dimensional face encoding from an image.
    
    Args:
        image_file: Image file containing a face
        
    Returns:
        numpy.ndarray: 128-dimensional face encoding
        
    Raises:
        FaceDetectionError: If face cannot be detected or encoded
    """
    if not BIOMETRIC_AVAILABLE:
        raise FaceDetectionError("Biometric features are not available. Please install required libraries.")
    
    try:
        # Load image
        image = load_image_from_file(image_file)
        
        # Generate face encodings
        face_encodings = face_recognition.face_encodings(image)
        
        if len(face_encodings) == 0:
            raise FaceDetectionError("No face detected for encoding")
        
        if len(face_encodings) > 1:
            raise FaceDetectionError("Multiple faces detected. Please ensure only one face is visible.")
        
        return face_encodings[0]
        
    except FaceDetectionError:
        raise
    except Exception as e:
        raise FaceDetectionError(f"Face encoding generation failed: {str(e)}")


def compare_faces(encoding1: np.ndarray, encoding2: np.ndarray, 
                  tolerance: float = 0.6) -> Tuple[bool, float]:
    """
    Compare two face encodings to determine if they match.
    
    Args:
        encoding1: First face encoding (128-dim array)
        encoding2: Second face encoding (128-dim array)
        tolerance: Matching threshold (default 0.6, lower is stricter)
        
    Returns:
        tuple: (is_match, distance)
            - is_match: Boolean indicating if faces match
            - distance: Face distance (0-1, lower means better match)
    """
    if not BIOMETRIC_AVAILABLE:
        raise BiometricError("Biometric features are not available. Please install required libraries.")
    
    try:
        # Convert to numpy arrays if they're lists
        if isinstance(encoding1, list):
            encoding1 = np.array(encoding1)
        if isinstance(encoding2, list):
            encoding2 = np.array(encoding2)
        
        # Calculate face distance
        distance = face_recognition.face_distance([encoding1], encoding2)[0]
        
        # Determine if it's a match
        is_match = distance <= tolerance
        
        return is_match, float(distance)
        
    except Exception as e:
        raise BiometricError(f"Face comparison failed: {str(e)}")


def validate_face_quality(image_file, blur_threshold: float = 100.0) -> Tuple[bool, List[str]]:
    """
    Validate face image quality for biometric use.
    
    Checks:
    - Face is detected
    - Face size is adequate
    - Image is not too blurry
    - Lighting is adequate
    
    Args:
        image_file: Face image file
        blur_threshold: Minimum Laplacian variance for blur detection (default: 100.0)
                       Lower values are more lenient (e.g., 70 for registration)
        
    Returns:
        tuple: (is_valid, issues)
            - is_valid: Boolean indicating if quality is acceptable
            - issues: List of quality issues found
    """
    if not BIOMETRIC_AVAILABLE:
        return False, ["Biometric features are not available. Please install required libraries."]
    
    issues = []
    
    try:
        # Load image
        image = load_image_from_file(image_file)
        
        # Check if face is detected
        face_locations = face_recognition.face_locations(image)
        
        if len(face_locations) == 0:
            issues.append("No face detected")
            return False, issues
        
        if len(face_locations) > 1:
            issues.append(f"Multiple faces detected ({len(face_locations)})")
            return False, issues
        
        # Check face size
        top, right, bottom, left = face_locations[0]
        face_width = right - left
        face_height = bottom - top
        
        min_size = settings.BIOMETRIC_SETTINGS.get('MIN_FACE_SIZE', (100, 100))
        if face_width < min_size[0] or face_height < min_size[1]:
            issues.append(f"Face too small ({face_width}x{face_height}). Minimum: {min_size[0]}x{min_size[1]}")
        
        # Check image blur (using Laplacian variance)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        if laplacian_var < blur_threshold:
            issues.append(f"Image is too blurry (score: {laplacian_var:.2f}, threshold: {blur_threshold})")
        
        # Check brightness (lenient thresholds to accommodate various lighting conditions)
        brightness = np.mean(gray)
        if brightness < 30:
            issues.append("Image is too dark")
        elif brightness > 220:
            issues.append("Image is too bright")
        
        # Return validation result
        is_valid = len(issues) == 0
        return is_valid, issues
        
    except Exception as e:
        issues.append(f"Quality validation failed: {str(e)}")
        return False, issues


def save_face_image(face_array: np.ndarray, output_path: str) -> None:
    """
    Save a face image array to a file.
    
    Args:
        face_array: Face image as numpy array
        output_path: Path to save the image
    """
    try:
        # Convert RGB to BGR for OpenCV
        bgr_image = cv2.cvtColor(face_array, cv2.COLOR_RGB2BGR)
        
        # Save image
        cv2.imwrite(output_path, bgr_image)
        
    except Exception as e:
        raise BiometricError(f"Failed to save face image: {str(e)}")


def encoding_to_json(encoding: np.ndarray) -> List[float]:
    """
    Convert face encoding numpy array to JSON-serializable list.
    
    Args:
        encoding: Face encoding as numpy array
        
    Returns:
        list: Face encoding as list of floats
    """
    return encoding.tolist()


def json_to_encoding(json_data: List[float]) -> np.ndarray:
    """
    Convert JSON face encoding back to numpy array.
    
    Args:
        json_data: Face encoding as list of floats
        
    Returns:
        numpy.ndarray: Face encoding as numpy array
    """
    return np.array(json_data)


def get_face_match_threshold() -> float:
    """
    Get the face matching threshold from settings.
    
    Returns:
        float: Face matching threshold (default 0.6)
    """
    if hasattr(settings, 'BIOMETRIC_SETTINGS'):
        return settings.BIOMETRIC_SETTINGS.get('FACE_MATCH_THRESHOLD', 0.6)
    return 0.6


def get_confidence_level(distance: float) -> Tuple[str, float]:
    """
    Convert face distance to human-readable confidence level.
    
    Args:
        distance: Face distance (0-1, lower is better match)
        
    Returns:
        tuple: (confidence_level, confidence_percentage)
            - confidence_level: String like "VERY_HIGH", "HIGH", "MEDIUM", "LOW", "VERY_LOW"
            - confidence_percentage: Confidence as percentage (0-100)
    """
    # Convert distance to confidence percentage (inverse relationship)
    # Distance 0.0 = 100% confidence, Distance 1.0 = 0% confidence
    confidence_percentage = max(0, min(100, (1.0 - distance) * 100))
    
    if distance <= 0.3:
        return "VERY_HIGH", confidence_percentage  # 95%+ confidence
    elif distance <= 0.4:
        return "HIGH", confidence_percentage       # 85-95% confidence
    elif distance <= 0.5:
        return "MEDIUM", confidence_percentage     # 75-85% confidence
    elif distance <= 0.6:
        return "LOW", confidence_percentage        # 65-75% confidence
    else:
        return "VERY_LOW", confidence_percentage   # <65% confidence


def get_adaptive_threshold(user_count: int) -> float:
    """
    Calculate adaptive threshold based on number of registered users.
    
    More users = stricter threshold to reduce false positives in 1:N matching.
    
    Args:
        user_count: Number of registered users with face recognition
        
    Returns:
        float: Adaptive threshold value
    """
    if user_count < 10:
        return 0.6  # Standard threshold for small databases
    elif user_count < 100:
        return 0.55  # Slightly stricter
    elif user_count < 1000:
        return 0.5  # Stricter for medium databases
    else:
        return 0.45  # Very strict for large databases


def draw_face_bounding_box(image: np.ndarray, face_location: Tuple[int, int, int, int],
                           label: str = "Face Detected", color: Tuple[int, int, int] = (0, 255, 0)) -> np.ndarray:
    """
    Draw a bounding box around a detected face with label.
    
    Args:
        image: Image as numpy array (RGB format)
        face_location: Tuple of (top, right, bottom, left)
        label: Text label to display above the box
        color: RGB color tuple for the box (default: green)
        
    Returns:
        numpy.ndarray: Image with bounding box drawn
    """
    if not BIOMETRIC_AVAILABLE:
        raise BiometricError("Biometric features are not available.")
    
    # Make a copy to avoid modifying original
    annotated_image = image.copy()
    
    top, right, bottom, left = face_location
    
    # Draw rectangle (convert RGB to BGR for OpenCV)
    cv2.rectangle(annotated_image, (left, top), (right, bottom), color[::-1], 3)
    
    # Add text label
    cv2.putText(annotated_image, label, (left, top - 10),
               cv2.FONT_HERSHEY_SIMPLEX, 0.9, color[::-1], 2)
    
    return annotated_image


# ============================================================================
# LIVENESS DETECTION INTEGRATION
# ============================================================================

def decode_base64_image(base64_string: str) -> np.ndarray:
    """
    Decode a base64 image string to numpy array.
    
    Args:
        base64_string: Base64 encoded image (with or without data URI prefix)
        
    Returns:
        numpy.ndarray: Image in BGR format (OpenCV)
    """
    if not BIOMETRIC_AVAILABLE:
        raise BiometricError("Biometric features are not available.")
    
    # Remove data URI prefix if present
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]
    
    # Decode base64
    image_data = base64.b64decode(base64_string)
    
    # Convert to numpy array
    nparr = np.frombuffer(image_data, np.uint8)
    
    # Decode image
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise BiometricError("Failed to decode image from base64")
    
    return image


def frames_from_base64_list(base64_frames: List[str]) -> List[np.ndarray]:
    """
    Convert list of base64 images to list of numpy arrays.
    
    Args:
        base64_frames: List of base64 encoded images
        
    Returns:
        List[np.ndarray]: List of images
    """
    return [decode_base64_image(frame) for frame in base64_frames]


def perform_liveness_verification(frames: List[np.ndarray], 
                                   require_blink: bool = True,
                                   require_movement: bool = False,
                                   check_photo_attack: bool = True) -> Dict:
    """
    Perform comprehensive liveness verification on video frames.
    
    Args:
        frames: List of video frames (numpy arrays in BGR format)
        require_blink: Whether blink detection must pass
        require_movement: Whether head movement detection must pass
        check_photo_attack: Whether to check for photo/screen attacks
        
    Returns:
        dict: {
            'is_live': bool,
            'confidence': float (0-1),
            'checks': {
                'blink': {'passed': bool, 'details': dict},
                'movement': {'passed': bool, 'details': dict},
                'photo_attack': {'passed': bool, 'details': dict}
            },
            'error': str or None
        }
    """
    if not BIOMETRIC_AVAILABLE:
        raise LivenessError("Biometric features are not available.")
    
    from .liveness_detection import LivenessDetector
    
    detector = LivenessDetector()
    
    results = {
        'is_live': False,
        'confidence': 0.0,
        'checks': {},
        'error': None
    }
    
    try:
        passed_checks = 0
        total_required = 0
        
        # 1. Blink detection
        if require_blink:
            total_required += 1
            try:
                blink_passed, blink_details = detector.detect_blink(frames)
                results['checks']['blink'] = {
                    'passed': blink_passed,
                    'details': blink_details
                }
                if blink_passed:
                    passed_checks += 1
            except Exception as e:
                results['checks']['blink'] = {
                    'passed': False,
                    'details': {'error': str(e)}
                }
        
        # 2. Head movement detection
        if require_movement:
            total_required += 1
            try:
                movement_passed, movement_details = detector.detect_head_movement(frames)
                results['checks']['movement'] = {
                    'passed': movement_passed,
                    'details': movement_details
                }
                if movement_passed:
                    passed_checks += 1
            except Exception as e:
                results['checks']['movement'] = {
                    'passed': False,
                    'details': {'error': str(e)}
                }
        
        # 3. Photo attack detection (on multiple frames)
        if check_photo_attack:
            total_required += 1
            try:
                # Check first, middle, and last frame
                frame_indices = [0, len(frames) // 2, -1]
                photo_results = []
                
                for idx in frame_indices:
                    if abs(idx) < len(frames):
                        is_real, photo_details = detector.detect_photo_attack(frames[idx])
                        photo_results.append(is_real)
                
                # Majority vote
                photo_passed = sum(photo_results) > len(photo_results) / 2
                results['checks']['photo_attack'] = {
                    'passed': photo_passed,
                    'details': {
                        'frames_checked': len(photo_results),
                        'frames_passed': sum(photo_results),
                        'is_real': photo_passed
                    }
                }
                if photo_passed:
                    passed_checks += 1
            except Exception as e:
                results['checks']['photo_attack'] = {
                    'passed': False,
                    'details': {'error': str(e)}
                }
        
        # Calculate confidence
        if total_required > 0:
            results['confidence'] = passed_checks / total_required
            results['is_live'] = passed_checks == total_required
        else:
            results['confidence'] = 1.0
            results['is_live'] = True
        
    except Exception as e:
        results['error'] = str(e)
        results['is_live'] = False
        results['confidence'] = 0.0
    
    return results


def verify_face_with_liveness(
    live_frames: List[np.ndarray],
    stored_encoding: Union[List[float], np.ndarray],
    tolerance: float = None,
    require_blink: bool = True,
    require_movement: bool = False
) -> Dict:
    """
    Verify face match with liveness detection.
    
    Args:
        live_frames: List of video frames from live capture
        stored_encoding: Stored face encoding to match against
        tolerance: Face matching tolerance (default from settings)
        require_blink: Whether blink detection is required
        require_movement: Whether head movement is required
        
    Returns:
        dict: {
            'verified': bool,
            'liveness': {...},
            'face_match': {
                'matched': bool,
                'distance': float,
                'score': float (0-100)
            },
            'error': str or None
        }
    """
    if not BIOMETRIC_AVAILABLE:
        raise BiometricError("Biometric features are not available.")
    
    if tolerance is None:
        tolerance = get_face_match_threshold()
    
    result = {
        'verified': False,
        'liveness': None,
        'face_match': None,
        'error': None
    }
    
    try:
        # 1. Perform liveness check
        liveness_result = perform_liveness_verification(
            frames=live_frames,
            require_blink=require_blink,
            require_movement=require_movement,
            check_photo_attack=True
        )
        result['liveness'] = liveness_result
        
        if not liveness_result['is_live']:
            result['error'] = 'Liveness check failed - possible spoofing attempt'
            return result
        
        # 2. Get face encoding from the best frame (middle frame usually has better quality)
        best_frame_idx = len(live_frames) // 2
        best_frame = live_frames[best_frame_idx]
        
        # Convert BGR to RGB for face_recognition
        rgb_frame = cv2.cvtColor(best_frame, cv2.COLOR_BGR2RGB)
        
        # Get face encoding
        face_encodings = face_recognition.face_encodings(rgb_frame)
        
        if len(face_encodings) == 0:
            result['error'] = 'No face detected in live capture'
            return result
        
        live_encoding = face_encodings[0]
        
        # 3. Compare with stored encoding
        if isinstance(stored_encoding, list):
            stored_encoding = np.array(stored_encoding)
        
        is_match, distance = compare_faces(stored_encoding, live_encoding, tolerance)
        
        # Convert distance to score (0-100, higher is better)
        score = max(0, (1 - distance) * 100)
        
        result['face_match'] = {
            'matched': is_match,
            'distance': distance,
            'score': round(score, 2)
        }
        
        # 4. Final verification
        result['verified'] = liveness_result['is_live'] and is_match
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def match_face_to_id_with_liveness(
    live_frames: List[np.ndarray],
    id_card_image: Union[np.ndarray, str],
    tolerance: float = None,
    require_blink: bool = True,
    require_movement: bool = False
) -> Dict:
    """
    Match live face to ID card photo with liveness detection.
    
    Args:
        live_frames: List of video frames from live capture
        id_card_image: ID card image (numpy array or file path)
        tolerance: Face matching tolerance
        require_blink: Whether blink detection is required
        require_movement: Whether head movement is required
        
    Returns:
        dict: {
            'verified': bool,
            'liveness': {...},
            'id_face_detected': bool,
            'face_match': {
                'matched': bool,
                'distance': float,
                'score': float (0-100)
            },
            'error': str or None
        }
    """
    if not BIOMETRIC_AVAILABLE:
        raise BiometricError("Biometric features are not available.")
    
    if tolerance is None:
        tolerance = get_face_match_threshold()
    
    result = {
        'verified': False,
        'liveness': None,
        'id_face_detected': False,
        'face_match': None,
        'error': None
    }
    
    try:
        # 1. Perform liveness check
        liveness_result = perform_liveness_verification(
            frames=live_frames,
            require_blink=require_blink,
            require_movement=require_movement,
            check_photo_attack=True
        )
        result['liveness'] = liveness_result
        
        if not liveness_result['is_live']:
            result['error'] = 'Liveness check failed - possible spoofing attempt'
            return result
        
        # 2. Extract face from ID card
        if isinstance(id_card_image, str):
            # It's a file path
            id_image = face_recognition.load_image_file(id_card_image)
        elif isinstance(id_card_image, np.ndarray):
            # It's already a numpy array (BGR from OpenCV)
            id_image = cv2.cvtColor(id_card_image, cv2.COLOR_BGR2RGB)
        else:
            # Try to load from file-like object
            id_image = face_recognition.load_image_file(id_card_image)
        
        id_face_encodings = face_recognition.face_encodings(id_image)
        
        if len(id_face_encodings) == 0:
            result['error'] = 'No face detected in ID card image'
            return result
        
        result['id_face_detected'] = True
        id_encoding = id_face_encodings[0]
        
        # 3. Get face encoding from live capture
        best_frame_idx = len(live_frames) // 2
        best_frame = live_frames[best_frame_idx]
        rgb_frame = cv2.cvtColor(best_frame, cv2.COLOR_BGR2RGB)
        
        live_face_encodings = face_recognition.face_encodings(rgb_frame)
        
        if len(live_face_encodings) == 0:
            result['error'] = 'No face detected in live capture'
            return result
        
        live_encoding = live_face_encodings[0]
        
        # 4. Compare faces
        is_match, distance = compare_faces(id_encoding, live_encoding, tolerance)
        score = max(0, (1 - distance) * 100)
        
        result['face_match'] = {
            'matched': is_match,
            'distance': distance,
            'score': round(score, 2)
        }
        
        # 5. Final verification
        result['verified'] = liveness_result['is_live'] and is_match
        
    except Exception as e:
        result['error'] = str(e)
    
    return result
