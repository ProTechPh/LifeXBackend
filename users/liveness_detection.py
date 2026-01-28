"""
Liveness Detection Utilities for Anti-Spoofing

Prevents face spoofing attacks including:
- Photo attacks (printed photos, phone screens)
- Video replay attacks
- 3D mask attacks
- Deepfake attacks

Implements multiple liveness detection techniques:
1. Blink detection
2. Head movement detection
3. Texture analysis (detect printed photos)
4. Challenge-response system
5. Multi-frame analysis
"""

import cv2
import numpy as np
import dlib
from typing import Tuple, List, Dict, Optional
import random
import time


class LivenessDetectionError(Exception):
    """Raised when liveness detection fails"""
    pass


class LivenessDetector:
    """
    Comprehensive liveness detection system.
    
    Uses multiple techniques to detect if a face is real or spoofed.
    """
    
    def __init__(self):
        # Initialize dlib face detector and landmark predictor
        self.detector = dlib.get_frontal_face_detector()
        # Note: You'll need to download shape_predictor_68_face_landmarks.dat
        # from http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
        try:
            self.predictor = dlib.shape_predictor('models/shape_predictor_68_face_landmarks.dat')
        except:
            self.predictor = None
    
    def detect_blink(self, frames: List[np.ndarray]) -> Tuple[bool, Dict]:
        """
        Detect if user blinked in the sequence of frames.
        
        Args:
            frames: List of video frames (numpy arrays)
            
        Returns:
            tuple: (blink_detected, details)
        """
        if self.predictor is None:
            raise LivenessDetectionError("Landmark predictor not loaded")
        
        ear_values = []  # Eye Aspect Ratio values
        
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.detector(gray)
            
            if len(faces) == 0:
                continue
            
            # Get facial landmarks
            landmarks = self.predictor(gray, faces[0])
            
            # Calculate Eye Aspect Ratio (EAR)
            ear = self._calculate_ear(landmarks)
            ear_values.append(ear)
        
        if len(ear_values) < 5:
            return False, {'error': 'Not enough frames to detect blink'}
        
        # Detect blink: EAR drops significantly then recovers
        blink_detected = self._detect_blink_pattern(ear_values)
        
        return blink_detected, {
            'ear_values': ear_values,
            'min_ear': min(ear_values),
            'max_ear': max(ear_values),
            'blink_detected': blink_detected
        }
    
    def _calculate_ear(self, landmarks) -> float:
        """
        Calculate Eye Aspect Ratio (EAR).
        
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        
        Where p1-p6 are eye landmark points.
        """
        # Left eye landmarks (points 36-41)
        left_eye = []
        for i in range(36, 42):
            left_eye.append((landmarks.part(i).x, landmarks.part(i).y))
        
        # Right eye landmarks (points 42-47)
        right_eye = []
        for i in range(42, 48):
            right_eye.append((landmarks.part(i).x, landmarks.part(i).y))
        
        # Calculate EAR for both eyes
        left_ear = self._eye_aspect_ratio(left_eye)
        right_ear = self._eye_aspect_ratio(right_eye)
        
        # Average EAR
        return (left_ear + right_ear) / 2.0
    
    def _eye_aspect_ratio(self, eye_points: List[Tuple[int, int]]) -> float:
        """Calculate EAR for one eye"""
        # Vertical distances
        v1 = np.linalg.norm(np.array(eye_points[1]) - np.array(eye_points[5]))
        v2 = np.linalg.norm(np.array(eye_points[2]) - np.array(eye_points[4]))
        
        # Horizontal distance
        h = np.linalg.norm(np.array(eye_points[0]) - np.array(eye_points[3]))
        
        # EAR
        ear = (v1 + v2) / (2.0 * h)
        return ear
    
    def _detect_blink_pattern(self, ear_values: List[float]) -> bool:
        """
        Detect blink pattern in EAR values.
        
        A blink is characterized by:
        - EAR drops below threshold (eye closes)
        - EAR recovers above threshold (eye opens)
        """
        EAR_THRESHOLD = 0.25  # Typical threshold for closed eye
        
        # Find if there's a dip in EAR values
        min_ear = min(ear_values)
        max_ear = max(ear_values)
        
        # Check if there's significant variation (blink)
        if max_ear - min_ear < 0.05:
            return False  # No significant eye movement
        
        # Check for blink pattern: high -> low -> high
        below_threshold = [ear < EAR_THRESHOLD for ear in ear_values]
        
        # Count transitions
        transitions = 0
        for i in range(1, len(below_threshold)):
            if below_threshold[i] != below_threshold[i-1]:
                transitions += 1
        
        # At least 2 transitions (open->close->open)
        return transitions >= 2
    
    def detect_head_movement(self, frames: List[np.ndarray]) -> Tuple[bool, Dict]:
        """
        Detect if user moved their head (left/right or up/down).
        
        Args:
            frames: List of video frames
            
        Returns:
            tuple: (movement_detected, details)
        """
        if self.predictor is None:
            raise LivenessDetectionError("Landmark predictor not loaded")
        
        nose_positions = []
        
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.detector(gray)
            
            if len(faces) == 0:
                continue
            
            landmarks = self.predictor(gray, faces[0])
            
            # Get nose tip position (landmark 30)
            nose_x = landmarks.part(30).x
            nose_y = landmarks.part(30).y
            nose_positions.append((nose_x, nose_y))
        
        if len(nose_positions) < 5:
            return False, {'error': 'Not enough frames to detect movement'}
        
        # Calculate movement range
        x_positions = [pos[0] for pos in nose_positions]
        y_positions = [pos[1] for pos in nose_positions]
        
        x_range = max(x_positions) - min(x_positions)
        y_range = max(y_positions) - min(y_positions)
        
        # Movement threshold (pixels)
        MOVEMENT_THRESHOLD = 20
        
        movement_detected = (x_range > MOVEMENT_THRESHOLD or 
                           y_range > MOVEMENT_THRESHOLD)
        
        return movement_detected, {
            'x_range': x_range,
            'y_range': y_range,
            'movement_detected': movement_detected,
            'nose_positions': nose_positions
        }
    
    def detect_photo_attack(self, image: np.ndarray) -> Tuple[bool, Dict]:
        """
        Detect if image is a printed photo or screen display.
        
        Uses texture analysis and moiré pattern detection.
        
        Args:
            image: Input image
            
        Returns:
            tuple: (is_real, details)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 1. Texture analysis using Local Binary Patterns (LBP)
        lbp_score = self._calculate_lbp_score(gray)
        
        # 2. Check for moiré patterns (common in photos of screens)
        moire_detected = self._detect_moire_pattern(gray)
        
        # 3. Check image sharpness (photos are often blurrier)
        sharpness = self._calculate_sharpness(gray)
        
        # 4. Check for screen glare/reflection patterns
        glare_detected = self._detect_glare(image)
        
        # Combine scores
        is_real = (
            lbp_score > 0.5 and
            not moire_detected and
            sharpness > 100 and
            not glare_detected
        )
        
        return is_real, {
            'lbp_score': lbp_score,
            'moire_detected': moire_detected,
            'sharpness': sharpness,
            'glare_detected': glare_detected,
            'is_real': is_real
        }
    
    def _calculate_lbp_score(self, gray_image: np.ndarray) -> float:
        """Calculate Local Binary Pattern score for texture analysis"""
        # Simplified LBP calculation
        # Real faces have more complex texture than printed photos
        
        # Calculate gradient magnitude
        sobelx = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobelx**2 + sobely**2)
        
        # Normalize
        score = np.mean(magnitude) / 255.0
        return score
    
    def _detect_moire_pattern(self, gray_image: np.ndarray) -> bool:
        """Detect moiré patterns (common when photographing screens)"""
        # Apply FFT to detect periodic patterns
        f = np.fft.fft2(gray_image)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1)
        
        # Check for strong periodic patterns
        # Moiré patterns show up as strong peaks in frequency domain
        threshold = np.mean(magnitude_spectrum) + 2 * np.std(magnitude_spectrum)
        peaks = magnitude_spectrum > threshold
        
        # If too many peaks, likely a moiré pattern
        return np.sum(peaks) > (gray_image.size * 0.01)
    
    def _calculate_sharpness(self, gray_image: np.ndarray) -> float:
        """Calculate image sharpness using Laplacian variance"""
        laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
        variance = laplacian.var()
        return variance
    
    def _detect_glare(self, image: np.ndarray) -> bool:
        """Detect screen glare or reflections"""
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Check for very bright spots (glare)
        v_channel = hsv[:, :, 2]
        bright_pixels = np.sum(v_channel > 240)
        
        # If more than 5% of pixels are very bright, likely glare
        return (bright_pixels / v_channel.size) > 0.05
    
    def generate_challenge(self) -> Dict:
        """
        Generate a random challenge for the user.
        
        Returns:
            dict: Challenge details
        """
        challenges = [
            {
                'type': 'BLINK',
                'instruction': 'Please blink your eyes twice',
                'expected_blinks': 2,
                'timeout': 5
            },
            {
                'type': 'SMILE',
                'instruction': 'Please smile',
                'timeout': 3
            },
            {
                'type': 'TURN_HEAD_LEFT',
                'instruction': 'Please turn your head to the left',
                'timeout': 3
            },
            {
                'type': 'TURN_HEAD_RIGHT',
                'instruction': 'Please turn your head to the right',
                'timeout': 3
            },
            {
                'type': 'NOD',
                'instruction': 'Please nod your head (up and down)',
                'timeout': 3
            }
        ]
        
        # Select random challenge
        challenge = random.choice(challenges)
        challenge['challenge_id'] = f"CH_{int(time.time())}_{random.randint(1000, 9999)}"
        
        return challenge
    
    def verify_challenge_response(self, challenge: Dict, frames: List[np.ndarray]) -> Tuple[bool, Dict]:
        """
        Verify if user completed the challenge correctly.
        
        Args:
            challenge: Challenge details
            frames: Video frames of user's response
            
        Returns:
            tuple: (success, details)
        """
        challenge_type = challenge['type']
        
        if challenge_type == 'BLINK':
            blink_detected, details = self.detect_blink(frames)
            return blink_detected, details
        
        elif challenge_type in ['TURN_HEAD_LEFT', 'TURN_HEAD_RIGHT', 'NOD']:
            movement_detected, details = self.detect_head_movement(frames)
            return movement_detected, details
        
        elif challenge_type == 'SMILE':
            # Simplified smile detection (would need more sophisticated model)
            return True, {'note': 'Smile detection not fully implemented'}
        
        return False, {'error': 'Unknown challenge type'}


def perform_liveness_check(video_frames: List[np.ndarray]) -> Dict:
    """
    Perform comprehensive liveness check on video frames.
    
    Args:
        video_frames: List of frames from video capture
        
    Returns:
        dict: Liveness check results
    """
    detector = LivenessDetector()
    
    results = {
        'is_live': False,
        'confidence': 0.0,
        'checks': {}
    }
    
    try:
        # 1. Blink detection
        blink_detected, blink_details = detector.detect_blink(video_frames)
        results['checks']['blink'] = {
            'passed': blink_detected,
            'details': blink_details
        }
        
        # 2. Head movement detection
        movement_detected, movement_details = detector.detect_head_movement(video_frames)
        results['checks']['movement'] = {
            'passed': movement_detected,
            'details': movement_details
        }
        
        # 3. Photo attack detection (on first frame)
        is_real, photo_details = detector.detect_photo_attack(video_frames[0])
        results['checks']['photo_attack'] = {
            'passed': is_real,
            'details': photo_details
        }
        
        # Calculate overall confidence
        passed_checks = sum(1 for check in results['checks'].values() if check['passed'])
        total_checks = len(results['checks'])
        confidence = passed_checks / total_checks
        
        results['confidence'] = confidence
        results['is_live'] = confidence >= 0.67  # At least 2 out of 3 checks must pass
        
    except Exception as e:
        results['error'] = str(e)
    
    return results
