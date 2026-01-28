"""
Face-Only Login (1:N Matching)

Allows users to login using ONLY their face, without entering email/username.

Process:
1. User captures face photo/video
2. System generates face encoding
3. System compares against ALL registered users (1:N matching)
4. If match found with high confidence, auto-login
5. If multiple matches or low confidence, ask for confirmation

Security considerations:
- Slower than 1:1 matching (must check all users)
- Requires higher confidence threshold
- Should include liveness detection
- Rate limiting to prevent brute force
"""

import numpy as np
from typing import Tuple, Optional, List, Dict
from django.contrib.auth import get_user_model
from .models import BiometricData
from .biometric_utils import (
    generate_face_encoding,
    compare_faces,
    json_to_encoding
)

User = get_user_model()


def identify_user_by_face(face_image, confidence_threshold: float = None, use_adaptive: bool = True) -> Tuple[Optional[User], float, List[Dict]]:
    """
    Identify user by face using 1:N matching with adaptive threshold.
    
    Compares submitted face against ALL registered users.
    
    Args:
        face_image: Face image file
        confidence_threshold: Maximum distance for match (None = use adaptive threshold)
        use_adaptive: Whether to use adaptive threshold based on user count (default: True)
        
    Returns:
        tuple: (matched_user, confidence_score, all_matches)
            - matched_user: User object if confident match found, None otherwise
            - confidence_score: Distance score (lower = better match)
            - all_matches: List of potential matches with scores and confidence levels
    """
    try:
        from .biometric_utils import get_adaptive_threshold, get_confidence_level
        
        # Generate encoding from submitted face
        submitted_encoding = generate_face_encoding(face_image)
        
        # Get all users with face recognition enabled
        # Accept both PENDING and CONFIRMED status since face is already verified
        biometric_users = BiometricData.objects.filter(
            face_recognition_enabled=True,
            is_face_verified=True,
            status__in=['PENDING', 'CONFIRMED']
        ).select_related('user')
        
        user_count = biometric_users.count()
        
        # Use adaptive threshold if enabled and no explicit threshold provided
        if confidence_threshold is None and use_adaptive:
            confidence_threshold = get_adaptive_threshold(user_count)
            print(f"[FACE LOGIN DEBUG] Using adaptive threshold: {confidence_threshold} for {user_count} users")
        elif confidence_threshold is None:
            confidence_threshold = 0.6  # Default threshold
        
        print(f"[FACE LOGIN DEBUG] Comparing against {user_count} registered users with threshold {confidence_threshold}")
        
        if user_count == 0:
            print("[FACE LOGIN DEBUG] No users with face recognition enabled")
            return None, 1.0, []
        
        # Compare against all users
        matches = []
        for biometric_data in biometric_users:
            stored_encoding = json_to_encoding(biometric_data.live_face_encoding)
            
            is_match, distance = compare_faces(
                stored_encoding,
                submitted_encoding,
                tolerance=confidence_threshold
            )
            
            # Get confidence level
            confidence_level, confidence_percentage = get_confidence_level(distance)
            
            print(f"[FACE LOGIN DEBUG] User: {biometric_data.user.email}, Distance: {distance:.4f}, "
                  f"Match: {is_match}, Confidence: {confidence_level} ({confidence_percentage:.1f}%)")
            
            matches.append({
                'user': biometric_data.user,
                'distance': distance,
                'is_match': is_match,
                'biometric_id': biometric_data.biometric_id,
                'confidence_level': confidence_level,
                'confidence_percentage': confidence_percentage
            })
        
        # Sort by distance (lower = better match)
        matches.sort(key=lambda x: x['distance'])
        
        if matches:
            best = matches[0]
            print(f"[FACE LOGIN DEBUG] Best match: {best['user'].email}, Distance: {best['distance']:.4f}, "
                  f"Confidence: {best['confidence_level']} ({best['confidence_percentage']:.1f}%)")
        
        # Check if we have a clear winner
        if len(matches) > 0 and matches[0]['is_match']:
            best_match = matches[0]
            print(f"[FACE LOGIN DEBUG] Match found! User: {best_match['user'].email}")
            
            # Check if there's a second close match (ambiguous)
            if len(matches) > 1:
                second_best = matches[1]
                # If second match is also very close, it's ambiguous
                if second_best['distance'] < (best_match['distance'] + 0.1):
                    print(f"[FACE LOGIN DEBUG] Ambiguous match - second best distance: {second_best['distance']:.4f}")
                    # Too close to call - return None but include candidates
                    return None, best_match['distance'], matches[:3]
            
            # Clear winner
            return best_match['user'], best_match['distance'], matches[:3]
        
        # No confident match
        print(f"[FACE LOGIN DEBUG] No match found. Best distance: {matches[0]['distance']:.4f if matches else 'N/A'}")
        return None, matches[0]['distance'] if matches else 1.0, matches[:3]
        
    except Exception as e:
        raise Exception(f"Face identification failed: {str(e)}")


def quick_face_login(face_image, use_adaptive: bool = True) -> Dict:
    """
    Quick face login without username using adaptive threshold.
    
    Args:
        face_image: Face image file
        use_adaptive: Whether to use adaptive threshold (default: True)
        
    Returns:
        dict: Login result with user info, confidence levels, or error
    """
    try:
        from .biometric_utils import get_confidence_level
        
        # Identify user by face with adaptive threshold
        user, distance, all_matches = identify_user_by_face(face_image, use_adaptive=use_adaptive)
        
        if user is None:
            if len(all_matches) > 1 and all_matches[0]['distance'] < 0.6:
                # Multiple possible matches - need confirmation
                return {
                    'status': 'AMBIGUOUS',
                    'message': 'Multiple possible matches found. Please confirm your identity.',
                    'candidates': [
                        {
                            'user_id': str(match['user'].id),
                            'name': match['user'].get_full_name(),
                            'email': match['user'].email[:3] + '***@' + match['user'].email.split('@')[1],
                            'distance': match['distance'],
                            'confidence_level': match.get('confidence_level', 'UNKNOWN'),
                            'confidence_percentage': match.get('confidence_percentage', 0.0)
                        }
                        for match in all_matches[:3]
                    ]
                }
            else:
                # No match found
                confidence_level, confidence_percentage = get_confidence_level(distance)
                return {
                    'status': 'NO_MATCH',
                    'message': 'Face not recognized. Please try again or use password login.',
                    'distance': distance,
                    'confidence_level': confidence_level,
                    'confidence_percentage': confidence_percentage
                }
        
        # Match found!
        confidence_level, confidence_percentage = get_confidence_level(distance)
        
        return {
            'status': 'SUCCESS',
            'message': f'Welcome back, {user.get_full_name()}!',
            'user': user,
            'distance': distance,
            'confidence_level': confidence_level,
            'confidence_percentage': confidence_percentage,
            'match_details': all_matches[0] if all_matches else None
        }
        
    except Exception as e:
        return {
            'status': 'ERROR',
            'message': f'Login failed: {str(e)}'
        }


def get_face_login_stats() -> Dict:
    """
    Get statistics about face login capability.
    
    Returns:
        dict: Statistics about registered users
    """
    total_users = User.objects.count()
    
    biometric_users = BiometricData.objects.filter(
        is_face_verified=True
    ).count()
    
    face_enabled_users = BiometricData.objects.filter(
        face_recognition_enabled=True,
        is_face_verified=True,
        status='CONFIRMED'
    ).count()
    
    return {
        'total_users': total_users,
        'biometric_registered': biometric_users,
        'face_login_enabled': face_enabled_users,
        'face_login_percentage': (face_enabled_users / total_users * 100) if total_users > 0 else 0
    }
