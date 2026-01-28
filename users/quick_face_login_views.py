"""
Quick Face Login View - No username/password needed!

User just shows their face and the system identifies them.
Includes confirmation step to prevent wrong account login.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.core.cache import cache
from django.contrib.auth import get_user_model
from blockchain.models import AuditLog
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .face_only_login import quick_face_login, get_face_login_stats, identify_user_by_face
import secrets
import time

User = get_user_model()


@extend_schema(
    tags=['Authentication'],
    summary='Quick Face Login (No Email Required)',
    description='''
    Login using ONLY face image - no email or password needed! (1:N matching)
    
    **Process:**
    1. User captures face photo
    2. System compares against ALL registered users with face recognition enabled
    3. If confident match found (distance < 0.5), auto-login
    4. If ambiguous (multiple close matches), returns candidates for confirmation
    5. If no match, suggests password login
    
    **Security:**
    - Rate limited: 5 attempts per minute per IP
    - High confidence threshold required
    - All attempts logged to audit trail
    - Should include liveness detection in production
    
    **Response Types:**
    - `success`: Clear match found, user logged in automatically
    - `ambiguous`: Multiple possible matches, user must select their account
    - `no_match`: Face not recognized in system
    ''',
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'face_image': {'type': 'string', 'format': 'binary', 'description': 'Face photo for identification'}
            },
            'required': ['face_image']
        }
    },
    responses={
        200: {
            'description': 'Success or ambiguous match',
            'content': {
                'application/json': {
                    'examples': {
                        'success': {
                            'summary': 'Clear match found',
                            'value': {
                                'status': 'success',
                                'message': 'Welcome back!',
                                'user': {
                                    'id': 'uuid',
                                    'email': 'user@example.com',
                                    'first_name': 'John',
                                    'last_name': 'Doe',
                                    'full_name': 'John Doe',
                                    'role': 'PATIENT'
                                },
                                'confidence': 0.95,
                                'tokens': {
                                    'refresh': 'refresh_token',
                                    'access': 'access_token'
                                }
                            }
                        },
                        'ambiguous': {
                            'summary': 'Multiple possible matches',
                            'value': {
                                'status': 'ambiguous',
                                'message': 'Multiple possible matches found',
                                'candidates': [
                                    {
                                        'user_id': 'uuid1',
                                        'full_name': 'John Doe',
                                        'email': 'joh***@example.com',
                                        'role': 'PATIENT',
                                        'confidence': 0.85
                                    }
                                ],
                                'instruction': 'Please select your account from the list below'
                            }
                        }
                    }
                }
            }
        },
        401: {'description': 'Face not recognized'},
        429: {'description': 'Too many attempts - rate limited'},
        500: {'description': 'Server error during face identification'}
    }
)
@method_decorator(never_cache, name='dispatch')
class QuickFaceLoginView(APIView):
    """
    Quick face login - NO username/password needed!
    
    POST /api/auth/quick-face-login/
    
    User just submits face image, system identifies them automatically.
    
    Process:
    1. User captures face photo
    2. System compares against ALL registered users (1:N matching)
    3. If confident match found, auto-login
    4. If ambiguous, show candidates for confirmation
    5. If no match, suggest password login
    
    Security:
    - Rate limited (5 attempts per minute per IP)
    - Requires high confidence threshold
    - Logs all attempts
    - Should include liveness detection in production
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Rate limiting
        ip_address = request.META.get('REMOTE_ADDR')
        cache_key = f'quick_face_login_{ip_address}'
        attempts = cache.get(cache_key, 0)
        
        if attempts >= 5:
            return Response({
                'error': 'Too many login attempts. Please try again in 1 minute.',
                'retry_after': 60
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Increment attempts
        cache.set(cache_key, attempts + 1, 60)  # 60 seconds timeout
        
        # Validate face image
        if 'face_image' not in request.FILES:
            return Response({
                'error': 'face_image is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        face_image = request.FILES['face_image']
        
        try:
            # Perform quick face login
            result = quick_face_login(face_image)
            
            if result['status'] == 'SUCCESS':
                user = result['user']
                
                # Check if account is active
                if not user.is_active:
                    return Response({
                        'error': 'Account is inactive'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                
                # Log successful login
                AuditLog.objects.create(
                    user=user,
                    action='QUICK_FACE_LOGIN_SUCCESS',
                    resource_type='User',
                    resource_id=str(user.id),
                    ip_address=ip_address,
                    details=f'Quick face login successful. Confidence: {result["confidence"]:.2%}'
                )
                
                # Clear rate limit on successful login
                cache.delete(cache_key)
                
                return Response({
                    'status': 'success',
                    'message': result['message'],
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'full_name': user.get_full_name(),
                        'role': user.role,
                    },
                    'confidence': result['confidence'],
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }, status=status.HTTP_200_OK)
            
            elif result['status'] == 'AMBIGUOUS':
                # Multiple possible matches - need user confirmation
                AuditLog.objects.create(
                    user=None,
                    action='QUICK_FACE_LOGIN_AMBIGUOUS',
                    resource_type='User',
                    resource_id='multiple',
                    ip_address=ip_address,
                    details=f'Ambiguous face match. Candidates: {len(result["candidates"])}'
                )
                
                return Response({
                    'status': 'ambiguous',
                    'message': result['message'],
                    'candidates': result['candidates'],
                    'instruction': 'Please select your account from the list below'
                }, status=status.HTTP_200_OK)
            
            else:
                # No match found
                AuditLog.objects.create(
                    user=None,
                    action='QUICK_FACE_LOGIN_FAILED',
                    resource_type='User',
                    resource_id='unknown',
                    ip_address=ip_address,
                    details=f'Face not recognized. Confidence: {result.get("confidence", 0):.2%}'
                )
                
                return Response({
                    'status': 'no_match',
                    'message': result['message'],
                    'suggestion': 'Try again with better lighting or use password login',
                    'fallback_url': '/api/auth/login/'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        except Exception as e:
            # Log error
            AuditLog.objects.create(
                user=None,
                action='QUICK_FACE_LOGIN_ERROR',
                resource_type='User',
                resource_id='error',
                ip_address=ip_address,
                details=f'Quick face login error: {str(e)}'
            )
            
            return Response({
                'error': f'Login failed: {str(e)}',
                'fallback_url': '/api/auth/login/'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmFaceLoginView(APIView):
    """
    Confirm identity when multiple matches found.
    
    POST /api/auth/confirm-face-login/
    
    When quick face login returns multiple candidates,
    user selects their account to complete login.
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        user_id = request.data.get('user_id')
        face_image = request.FILES.get('face_image')
        
        if not user_id or not face_image:
            return Response({
                'error': 'user_id and face_image are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django.contrib.auth import get_user_model
            from .biometric_utils import generate_face_encoding, compare_faces
            from .biometric_utils import json_to_encoding
            
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            # Verify face matches selected user
            submitted_encoding = generate_face_encoding(face_image)
            stored_encoding = json_to_encoding(user.biometric_data.live_face_encoding)
            
            is_match, distance = compare_faces(stored_encoding, submitted_encoding, tolerance=0.6)
            
            if not is_match:
                return Response({
                    'error': 'Face does not match selected account'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            # Log successful confirmation
            AuditLog.objects.create(
                user=user,
                action='QUICK_FACE_LOGIN_CONFIRMED',
                resource_type='User',
                resource_id=str(user.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'Face login confirmed after ambiguous match. Distance: {distance:.3f}'
            )
            
            return Response({
                'status': 'success',
                'message': f'Welcome back, {user.get_full_name()}!',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Confirmation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Authentication'],
    summary='Identify User by Face (Step 1 of 2)',
    description='''
    Identify user by face WITHOUT logging them in yet. Returns user preview for confirmation.
    
    **Two-Step Process:**
    1. **Identify** (this endpoint): System identifies user and returns preview
    2. **Confirm** (next endpoint): User confirms "Yes, this is me" to complete login
    
    **Security Benefits:**
    - User sees who the system thinks they are before login
    - Prevents accidental login to wrong account
    - User can reject if identification is wrong
    - Session token expires in 60 seconds
    ''',
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'face_image': {'type': 'string', 'format': 'binary'}
            },
            'required': ['face_image']
        }
    },
    responses={
        200: {
            'description': 'User identified or ambiguous match',
            'content': {
                'application/json': {
                    'examples': {
                        'identified': {
                            'summary': 'User identified successfully',
                            'value': {
                                'status': 'identified',
                                'message': 'We found a match. Please confirm if this is you.',
                                'user_preview': {
                                    'user_id': 'uuid',
                                    'full_name': 'John Doe',
                                    'email_masked': 'joh***@example.com',
                                    'role': 'PATIENT',
                                    'last_login': '2026-01-28T10:00:00Z'
                                },
                                'confidence': 0.95,
                                'confidence_level': 'VERY HIGH',
                                'session_token': 'session_token_here',
                                'expires_in': 60
                            }
                        }
                    }
                }
            }
        },
        401: {'description': 'Face not recognized'},
        429: {'description': 'Too many attempts'}
    }
)
class IdentifyFaceView(APIView):
    """
    Identify user by face WITHOUT logging them in yet.
    
    POST /api/auth/identify-face/
    
    Returns user preview for confirmation.
    User must confirm identity before actual login.
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Rate limiting
        ip_address = request.META.get('REMOTE_ADDR')
        cache_key = f'identify_face_{ip_address}'
        attempts = cache.get(cache_key, 0)
        
        if attempts >= 5:
            return Response({
                'error': 'Too many identification attempts. Please try again in 1 minute.',
                'retry_after': 60
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        cache.set(cache_key, attempts + 1, 60)
        
        # Validate face image
        if 'face_image' not in request.FILES:
            return Response({
                'error': 'face_image is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        face_image = request.FILES['face_image']
        
        try:
            # Identify user (1:N matching)
            user, confidence, all_matches = identify_user_by_face(face_image)
            
            if user is None:
                if len(all_matches) > 1 and all_matches[0]['distance'] < 0.6:
                    # Multiple possible matches - need user to select
                    session_token = secrets.token_urlsafe(32)
                    
                    # Store candidates in cache
                    cache.set(f'face_session_{session_token}', {
                        'candidates': [
                            {
                                'user_id': str(match['user'].id),
                                'confidence': 1.0 - match['distance']
                            }
                            for match in all_matches[:3]
                        ],
                        'expires': time.time() + 60
                    }, timeout=60)
                    
                    # Log ambiguous match
                    AuditLog.objects.create(
                        user=None,
                        action='FACE_IDENTIFICATION_AMBIGUOUS',
                        resource_type='User',
                        resource_id='multiple',
                        ip_address=ip_address,
                        details=f'Ambiguous face match. Candidates: {len(all_matches)}'
                    )
                    
                    return Response({
                        'status': 'ambiguous',
                        'message': 'Multiple possible matches. Please select your account.',
                        'candidates': [
                            {
                                'user_id': str(match['user'].id),
                                'full_name': match['user'].get_full_name(),
                                'email_masked': match['user'].email[:3] + '***@' + match['user'].email.split('@')[1],
                                'role': match['user'].role,
                                'confidence': 1.0 - match['distance']
                            }
                            for match in all_matches[:3]
                        ],
                        'session_token': session_token,
                        'expires_in': 60
                    }, status=status.HTTP_200_OK)
                else:
                    # No match found
                    AuditLog.objects.create(
                        user=None,
                        action='FACE_IDENTIFICATION_FAILED',
                        resource_type='User',
                        resource_id='unknown',
                        ip_address=ip_address,
                        details=f'Face not recognized. Best distance: {all_matches[0]["distance"] if all_matches else 1.0}'
                    )
                    
                    return Response({
                        'status': 'not_found',
                        'message': 'Face not recognized in our system.',
                        'confidence': 1.0 - confidence if confidence < 1.0 else 0.0,
                        'suggestions': [
                            'Try again with better lighting',
                            'Remove glasses or mask',
                            'Use password login instead'
                        ]
                    }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Match found! Generate session token
            session_token = secrets.token_urlsafe(32)
            
            # Store identification in cache (expires in 60 seconds)
            cache.set(f'face_session_{session_token}', {
                'user_id': str(user.id),
                'confidence': 1.0 - confidence,
                'expires': time.time() + 60
            }, timeout=60)
            
            # Get confidence level
            confidence_score = 1.0 - confidence
            if confidence_score > 0.95:
                confidence_level = 'VERY HIGH'
            elif confidence_score > 0.80:
                confidence_level = 'HIGH'
            elif confidence_score > 0.70:
                confidence_level = 'MEDIUM'
            else:
                confidence_level = 'LOW'
            
            # Log identification
            AuditLog.objects.create(
                user=user,
                action='FACE_IDENTIFICATION_SUCCESS',
                resource_type='User',
                resource_id=str(user.id),
                ip_address=ip_address,
                details=f'Face identified. Confidence: {confidence_score:.2%}, Level: {confidence_level}'
            )
            
            # Return user preview for confirmation
            return Response({
                'status': 'identified',
                'message': 'We found a match. Please confirm if this is you.',
                'user_preview': {
                    'user_id': str(user.id),
                    'full_name': user.get_full_name(),
                    'email_masked': user.email[:3] + '***@' + user.email.split('@')[1],
                    'role': user.role,
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                    'date_joined': user.date_joined.isoformat()
                },
                'confidence': confidence_score,
                'confidence_level': confidence_level,
                'session_token': session_token,
                'expires_in': 60
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            AuditLog.objects.create(
                user=None,
                action='FACE_IDENTIFICATION_ERROR',
                resource_type='User',
                resource_id='error',
                ip_address=ip_address,
                details=f'Face identification error: {str(e)}'
            )
            
            return Response({
                'error': f'Identification failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Authentication'],
    summary='Confirm Identity and Login (Step 2 of 2)',
    description='''
    User confirms their identity and completes the login process.
    
    **Process:**
    1. User receives session_token and user_id from identify-face endpoint
    2. User reviews the identified account information
    3. User confirms "Yes, this is me" (confirmed=true) or rejects (confirmed=false)
    4. If confirmed, JWT tokens are generated and user is logged in
    
    **Security:**
    - Session token expires in 60 seconds
    - User must explicitly confirm identity
    - All attempts logged to audit trail
    ''',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'session_token': {'type': 'string', 'description': 'Session token from identify-face'},
                'user_id': {'type': 'string', 'format': 'uuid', 'description': 'User ID to confirm'},
                'confirmed': {'type': 'boolean', 'description': 'True to confirm, false to reject'}
            },
            'required': ['session_token', 'user_id', 'confirmed']
        }
    },
    responses={
        200: {
            'description': 'Identity confirmed and logged in',
            'content': {
                'application/json': {
                    'example': {
                        'status': 'success',
                        'message': 'Welcome back, John Doe!',
                        'user': {
                            'id': 'uuid',
                            'email': 'user@example.com',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'full_name': 'John Doe',
                            'role': 'PATIENT'
                        },
                        'tokens': {
                            'refresh': 'refresh_token',
                            'access': 'access_token'
                        }
                    }
                }
            }
        },
        401: {'description': 'Session expired or invalid'},
        404: {'description': 'User not found'}
    }
)
class ConfirmIdentityView(APIView):
    """
    Confirm identity and complete login.
    
    POST /api/auth/confirm-identity/
    
    User confirms "Yes, this is me" and gets logged in.
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        session_token = request.data.get('session_token')
        user_id = request.data.get('user_id')
        confirmed = request.data.get('confirmed', False)
        
        if not session_token or not user_id:
            return Response({
                'error': 'session_token and user_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get session data from cache
        cache_key = f'face_session_{session_token}'
        session_data = cache.get(cache_key)
        
        if not session_data:
            return Response({
                'error': 'Session expired or invalid. Please try again.',
                'expired': True
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if session expired
        if session_data.get('expires', 0) < time.time():
            cache.delete(cache_key)
            return Response({
                'error': 'Session expired. Please identify again.',
                'expired': True
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            user = User.objects.get(id=user_id)
            
            # Verify user_id matches session
            if 'user_id' in session_data:
                if session_data['user_id'] != str(user.id):
                    return Response({
                        'error': 'User ID mismatch'
                    }, status=status.HTTP_400_BAD_REQUEST)
            elif 'candidates' in session_data:
                # Check if user_id is in candidates
                candidate_ids = [c['user_id'] for c in session_data['candidates']]
                if str(user.id) not in candidate_ids:
                    return Response({
                        'error': 'User ID not in candidates'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            ip_address = request.META.get('REMOTE_ADDR')
            
            if not confirmed:
                # User rejected the identification
                AuditLog.objects.create(
                    user=user,
                    action='FACE_IDENTITY_REJECTED',
                    resource_type='User',
                    resource_id=str(user.id),
                    ip_address=ip_address,
                    details='User rejected face identification'
                )
                
                # Delete session
                cache.delete(cache_key)
                
                return Response({
                    'status': 'rejected',
                    'message': 'Identity not confirmed. Please try again.',
                    'fallback_url': '/api/auth/login/'
                }, status=status.HTTP_200_OK)
            
            # User confirmed! Complete login
            if not user.is_active:
                return Response({
                    'error': 'Account is inactive'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Log successful confirmation
            AuditLog.objects.create(
                user=user,
                action='FACE_IDENTITY_CONFIRMED',
                resource_type='User',
                resource_id=str(user.id),
                ip_address=ip_address,
                details=f'Face identity confirmed. Confidence: {session_data.get("confidence", 0):.2%}'
            )
            
            # Delete session
            cache.delete(cache_key)
            
            return Response({
                'status': 'success',
                'message': f'Welcome back, {user.get_full_name()}!',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': user.get_full_name(),
                    'role': user.role,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Confirmation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Authentication'],
    summary='Face Login Statistics',
    description='Get statistics about face login capability in the system.',
    responses={
        200: {
            'description': 'Face login statistics',
            'content': {
                'application/json': {
                    'example': {
                        'total_users': 150,
                        'biometric_registered': 120,
                        'face_login_enabled': 100,
                        'face_login_percentage': '66.7%',
                        'message': '100 users can use quick face login'
                    }
                }
            }
        }
    }
)
class FaceLoginStatsView(APIView):
    """
    Get statistics about face login capability.
    
    GET /api/auth/face-login-stats/
    
    Returns info about how many users have face login enabled.
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        stats = get_face_login_stats()
        
        return Response({
            'total_users': stats['total_users'],
            'biometric_registered': stats['biometric_registered'],
            'face_login_enabled': stats['face_login_enabled'],
            'face_login_percentage': f"{stats['face_login_percentage']:.1f}%",
            'message': f"{stats['face_login_enabled']} users can use quick face login"
        }, status=status.HTTP_200_OK)
