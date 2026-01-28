"""
API views for biometric authentication.

Provides endpoints for:
- Biometric registration with ID card and face matching
- Face recognition login
- Managing face recognition settings
- Staff verification of biometric data
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import BiometricData
from .biometric_serializers import (
    BiometricDataSerializer,
    IDCardUploadSerializer,
    LiveFaceUploadSerializer,
    BiometricRegistrationSerializer,
    FaceLoginSerializer,
    ToggleFaceRecognitionSerializer,
    BiometricVerificationSerializer,
    LivenessVerificationSerializer,
    FaceMatchWithLivenessSerializer,
    FaceLoginWithLivenessSerializer,
    IDMatchWithLivenessSerializer,
)
from .biometric_blockchain import verify_biometric_on_blockchain, hash_biometric_data
from .face_only_login import quick_face_login, identify_user_by_face
from .permissions import IsAdmin, IsReceptionist
from blockchain.models import AuditLog

User = get_user_model()


@extend_schema(
    tags=['Authentication'],
    summary='Register with Biometric Authentication',
    description='''
    Complete user registration with biometric verification (ID card + face matching).
    
    **Process:**
    1. Validates user data
    2. Extracts text from ID card using OCR
    3. Detects face in ID card (if present)
    4. Generates face encoding from live photo
    5. Compares faces (if ID has face)
    6. Creates user and biometric data
    7. Returns JWT tokens
    
    **Required Fields:**
    - email, password, password2
    - id_card_image (file upload)
    - id_card_type (DRIVERS_LICENSE, PASSPORT, NATIONAL_ID, etc.)
    - live_face_image (file upload)
    
    **Optional Fields:**
    - first_name, last_name
    ''',
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'},
                'password': {'type': 'string', 'format': 'password', 'minLength': 8},
                'password2': {'type': 'string', 'format': 'password', 'minLength': 8},
                'first_name': {'type': 'string'},
                'last_name': {'type': 'string'},
                'id_card_image': {'type': 'string', 'format': 'binary'},
                'id_card_type': {
                    'type': 'string',
                    'enum': ['DRIVERS_LICENSE', 'PASSPORT', 'NATIONAL_ID', 'SSS_ID', 'UMID', 'PHILHEALTH_ID', 'POSTAL_ID', 'VOTERS_ID', 'PRC_ID', 'OTHER']
                },
                'live_face_image': {'type': 'string', 'format': 'binary'}
            },
            'required': ['email', 'password', 'password2', 'id_card_image', 'id_card_type', 'live_face_image']
        }
    },
    responses={
        201: {
            'description': 'Registration successful',
            'content': {
                'application/json': {
                    'example': {
                        'message': 'User registered successfully with biometric authentication',
                        'user': {
                            'id': 'uuid',
                            'email': 'user@example.com',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'role': 'PATIENT'
                        },
                        'biometric': {
                            'is_face_verified': True,
                            'face_match_score': 0.35,
                            'face_recognition_enabled': False
                        },
                        'tokens': {
                            'refresh': 'refresh_token_here',
                            'access': 'access_token_here'
                        }
                    }
                }
            }
        },
        400: {'description': 'Invalid input or face does not match ID'},
        500: {'description': 'Server error during registration'}
    }
)
class BiometricRegistrationView(APIView):
    """
    Complete biometric registration with ID card and face matching.
    
    POST /api/auth/register-with-biometrics/
    
    Accepts:
    - email, password, password2, first_name, last_name
    - id_card_image, id_card_type
    - live_face_image
    
    Process:
    1. Validates user data
    2. Extracts text from ID card using OCR
    3. Detects face in ID card (if present)
    4. Generates face encoding from live photo
    5. Compares faces (if ID has face)
    6. Creates user and biometric data
    7. Returns JWT tokens
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = BiometricRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Create user with biometric data
                user = serializer.save()
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                
                # Log the registration
                AuditLog.objects.create(
                    user=user,
                    action='BIOMETRIC_REGISTRATION',
                    resource_type='User',
                    resource_id=str(user.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details='User registered with biometric authentication'
                )
                
                return Response({
                    'message': 'User registered successfully with biometric authentication',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'role': user.role,
                    },
                    'biometric': {
                        'is_face_verified': user.biometric_data.is_face_verified,
                        'face_match_score': user.biometric_data.face_match_score,
                        'face_recognition_enabled': user.biometric_data.face_recognition_enabled,
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'error': f'Registration failed: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Upload and Process ID Card',
    description='''
    Step 1 of biometric registration: Upload ID card for OCR processing.
    
    **Process:**
    1. Validates ID card image
    2. Extracts text using OCR
    3. Detects face in ID card (if present)
    4. Returns extracted data
    
    **Use this endpoint to:**
    - Preview extracted data before registration
    - Verify ID card is readable
    - Check if face is detected in ID
    ''',
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'id_card_image': {'type': 'string', 'format': 'binary'},
                'id_card_type': {
                    'type': 'string',
                    'enum': ['DRIVERS_LICENSE', 'PASSPORT', 'NATIONAL_ID', 'SSS_ID', 'UMID', 'PHILHEALTH_ID', 'POSTAL_ID', 'VOTERS_ID', 'PRC_ID', 'OTHER']
                }
            },
            'required': ['id_card_image', 'id_card_type']
        }
    },
    responses={
        200: {
            'description': 'ID card processed successfully',
            'content': {
                'application/json': {
                    'example': {
                        'message': 'ID card processed successfully',
                        'extracted_data': {
                            'name': 'JUAN DELA CRUZ',
                            'id_number': '1234-5678-9012',
                            'address': '123 Main St, Manila'
                        },
                        'has_face': True,
                        'face_detected': True
                    }
                }
            }
        },
        400: {'description': 'Invalid image or processing failed'},
        500: {'description': 'Server error during OCR processing'}
    }
)
class IDCardUploadView(APIView):
    """
    Step 1: Upload and process ID card.
    
    POST /api/auth/upload-id-card/
    
    Accepts:
    - id_card_image
    - id_card_type
    
    Returns:
    - Extracted text information
    - Whether face was detected
    - Preview of extracted data
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = IDCardUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Process ID card
                result = serializer.process_id_card()
                
                return Response({
                    'message': 'ID card processed successfully',
                    'extracted_data': result['extracted_text'],
                    'has_face': result['has_face'],
                    'face_detected': result['has_face'],
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'error': f'ID card processing failed: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Verify Face Matches ID Card',
    description='''
    Step 2 of biometric registration: Verify that live face photo matches ID card photo.
    
    **Process:**
    1. Generates face encoding from live photo
    2. Extracts face from ID card
    3. Compares both faces
    4. Returns match result and confidence score
    
    **Use this endpoint to:**
    - Verify identity before completing registration
    - Test face matching accuracy
    - Preview match results
    ''',
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'live_face_image': {'type': 'string', 'format': 'binary'},
                'id_card_image': {'type': 'string', 'format': 'binary'},
                'id_card_type': {
                    'type': 'string',
                    'enum': ['DRIVERS_LICENSE', 'PASSPORT', 'NATIONAL_ID', 'SSS_ID', 'UMID', 'PHILHEALTH_ID', 'POSTAL_ID', 'VOTERS_ID', 'PRC_ID', 'OTHER']
                }
            },
            'required': ['live_face_image', 'id_card_image']
        }
    },
    responses={
        200: {
            'description': 'Face verification completed',
            'content': {
                'application/json': {
                    'example': {
                        'match': True,
                        'confidence_score': 0.35,
                        'threshold': 0.6,
                        'message': 'Face matches ID card'
                    }
                }
            }
        },
        400: {'description': 'Invalid input or no face detected'},
        500: {'description': 'Server error during face verification'}
    }
)
class FaceMatchVerificationView(APIView):
    """
    Step 2: Verify face matches ID card.
    
    POST /api/auth/verify-face-match/
    
    Accepts:
    - live_face_image
    - id_card_image (for comparison)
    - id_card_type
    
    Returns:
    - Match result (true/false)
    - Confidence score
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .biometric_utils import (
            generate_face_encoding,
            compare_faces,
            get_face_match_threshold,
            FaceDetectionError
        )
        
        # Validate required fields
        if 'live_face_image' not in request.data:
            return Response({
                'error': 'live_face_image is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if 'id_card_image' not in request.data:
            return Response({
                'error': 'id_card_image is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Process live face
            live_serializer = LiveFaceUploadSerializer(data={'live_face_image': request.data['live_face_image']})
            if not live_serializer.is_valid():
                return Response(live_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            live_result = live_serializer.process_live_face()
            live_encoding = live_result['face_encoding']
            
            # Process ID card
            id_serializer = IDCardUploadSerializer(data={
                'id_card_image': request.data['id_card_image'],
                'id_card_type': request.data.get('id_card_type', 'OTHER')
            })
            if not id_serializer.is_valid():
                return Response(id_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            id_result = id_serializer.process_id_card()
            
            if not id_result['has_face']:
                return Response({
                    'error': 'No face detected in ID card'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            id_encoding = id_result['face_encoding']
            
            # Compare faces
            threshold = get_face_match_threshold()
            is_match, distance = compare_faces(id_encoding, live_encoding, tolerance=threshold)
            
            return Response({
                'match': is_match,
                'confidence_score': float(distance),
                'threshold': threshold,
                'message': 'Face matches ID card' if is_match else 'Face does not match ID card'
            }, status=status.HTTP_200_OK)
            
        except FaceDetectionError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Face verification failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Authentication'],
    summary='Face Recognition Login',
    description='''
    Login using email and face image (1:1 matching).
    
    **Process:**
    1. User provides email and face photo
    2. System retrieves stored face encoding for that email
    3. Compares submitted face with stored encoding
    4. If match (distance ≤ 0.6), login successful
    
    **Security:**
    - Requires face recognition to be enabled for the account
    - Uses 128-dimensional face encoding comparison
    - Blockchain-verified biometric data
    - Audit logging for all attempts
    ''',
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'},
                'face_image': {'type': 'string', 'format': 'binary'}
            },
            'required': ['email', 'face_image']
        }
    },
    responses={
        200: {
            'description': 'Login successful',
            'content': {
                'application/json': {
                    'example': {
                        'message': 'Login successful',
                        'user': {
                            'id': 'uuid',
                            'email': 'user@example.com',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'role': 'PATIENT'
                        },
                        'tokens': {
                            'refresh': 'refresh_token_here',
                            'access': 'access_token_here'
                        }
                    }
                }
            }
        },
        400: {'description': 'Invalid input or face does not match'},
        403: {'description': 'Account is inactive'},
        500: {'description': 'Server error during face verification'}
    }
)
@method_decorator(never_cache, name='dispatch')
class FaceLoginView(APIView):
    """
    Face recognition login.
    
    POST /api/auth/login-with-face/
    
    Accepts:
    - email
    - face_image
    
    Returns:
    - User data
    - JWT tokens
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = FaceLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Get validated user
                user = serializer.validated_data['user']
                match_score = serializer.validated_data['match_score']
                
                # Check if account is active
                if not user.is_active:
                    return Response({
                        'error': 'Account is inactive'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                
                # Log the login
                AuditLog.objects.create(
                    user=user,
                    action='FACE_LOGIN',
                    resource_type='User',
                    resource_id=str(user.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f'Face recognition login successful. Match score: {match_score:.3f}'
                )
                
                return Response({
                    'message': 'Login successful',
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
                
            except Exception as e:
                return Response({
                    'error': f'Login failed: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FaceRecognitionStatusView(APIView):
    """
    Check if user has face recognition enabled.
    
    GET /api/auth/face-recognition-status/
    
    Returns:
    - enabled: Boolean
    - has_biometric_data: Boolean
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        has_biometric_data = hasattr(user, 'biometric_data')
        enabled = False
        
        if has_biometric_data:
            enabled = user.biometric_data.face_recognition_enabled
        
        return Response({
            'has_biometric_data': has_biometric_data,
            'enabled': enabled,
            'is_verified': user.biometric_data.is_face_verified if has_biometric_data else False
        }, status=status.HTTP_200_OK)


class ToggleFaceRecognitionView(APIView):
    """
    Enable or disable face recognition login.
    
    POST /api/auth/toggle-face-recognition/
    
    Accepts:
    - enable: Boolean
    - password: String (for security confirmation)
    
    Returns:
    - Success message
    - New status
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ToggleFaceRecognitionSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                user = request.user
                enable = serializer.validated_data['enable']
                
                biometric_data = user.biometric_data
                
                if enable:
                    biometric_data.enable_face_recognition()
                    message = 'Face recognition login enabled'
                    action = 'ENABLE_FACE_RECOGNITION'
                else:
                    biometric_data.disable_face_recognition()
                    message = 'Face recognition login disabled'
                    action = 'DISABLE_FACE_RECOGNITION'
                
                # Log the action
                AuditLog.objects.create(
                    user=user,
                    action=action,
                    resource_type='BiometricData',
                    resource_id=str(biometric_data.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=message
                )
                
                return Response({
                    'message': message,
                    'enabled': biometric_data.face_recognition_enabled
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'error': f'Failed to toggle face recognition: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BiometricDataDetailView(RetrieveAPIView):
    """
    View biometric data for a specific user.
    
    GET /api/biometrics/user/<user_id>/
    
    Permissions:
    - Admin/Receptionist can view any user
    - Users can view their own data
    """
    
    serializer_class = BiometricDataSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        user_id = self.kwargs.get('user_id')
        user = self.request.user
        
        # Check permissions
        if not (user.role in ['ADMIN', 'RECEPTIONIST'] or str(user.id) == user_id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to view this biometric data")
        
        try:
            target_user = User.objects.get(id=user_id)
            return target_user.biometric_data
        except User.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("User not found")
        except BiometricData.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Biometric data not found for this user")


class PendingBiometricVerificationsView(ListAPIView):
    """
    List users with unverified biometric data.
    
    GET /api/biometrics/pending-verifications/
    
    Permissions: Admin or Receptionist only
    """
    
    serializer_class = BiometricDataSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsReceptionist]
    
    def get_queryset(self):
        return BiometricData.objects.filter(
            is_face_verified=False
        ).select_related('user').order_by('-created_at')


class VerifyBiometricDataView(APIView):
    """
    Manually verify or reject biometric data.
    
    POST /api/biometrics/verify/<user_id>/
    
    Accepts:
    - approved: Boolean
    - notes: String (optional)
    
    Permissions: Admin or Receptionist only
    """
    
    permission_classes = [IsAuthenticated, IsAdmin | IsReceptionist]
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            biometric_data = user.biometric_data
            
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except BiometricData.DoesNotExist:
            return Response({
                'error': 'Biometric data not found for this user'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = BiometricVerificationSerializer(
            instance=biometric_data,
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Log the verification
            AuditLog.objects.create(
                user=request.user,
                action='VERIFY_BIOMETRIC_DATA',
                resource_type='BiometricData',
                resource_id=str(biometric_data.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Biometric data {'approved' if serializer.validated_data['approved'] else 'rejected'} for user {user.email}"
            )
            
            return Response({
                'message': 'Biometric data verification updated',
                'biometric_data': BiometricDataSerializer(biometric_data).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckBiometricIntegrityView(APIView):
    """
    Check if biometric data has been tampered with by verifying against blockchain.
    
    GET /api/biometrics/check-integrity/<user_id>/
    
    Returns:
    - is_valid: Boolean (true if data matches blockchain)
    - current_hash: Current hash of biometric data
    - blockchain_hash: Hash stored on blockchain
    - match: Boolean (true if hashes match)
    - message: Explanation
    
    Permissions: Admin, Receptionist, or own data
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        user = request.user
        
        # Check permissions
        if not (user.role in ['ADMIN', 'RECEPTIONIST'] or str(user.id) == user_id):
            return Response({
                'error': "You don't have permission to check this biometric data"
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            target_user = User.objects.get(id=user_id)
            biometric_data = target_user.biometric_data
            
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except BiometricData.DoesNotExist:
            return Response({
                'error': 'Biometric data not found for this user'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            from .biometric_blockchain import (
                verify_biometric_on_blockchain,
                hash_biometric_data
            )
            
            # Recalculate current hash
            current_hash = hash_biometric_data(
                biometric_data.id_card_image,
                biometric_data.live_face_image,
                biometric_data.id_face_encoding,
                biometric_data.live_face_encoding
            )
            
            # Compare with stored hash
            stored_hash = biometric_data.biometric_hash
            hashes_match = (current_hash == stored_hash)
            
            # Verify against blockchain
            blockchain_result = verify_biometric_on_blockchain(target_user, biometric_data)
            
            # Determine overall integrity
            is_valid = hashes_match and blockchain_result['is_valid']
            
            if is_valid:
                message = "✅ Biometric data is valid and has not been tampered with"
            elif not hashes_match:
                message = "❌ WARNING: Biometric data has been modified! Hash mismatch detected."
            else:
                message = "❌ WARNING: Blockchain verification failed!"
            
            # Log the integrity check
            AuditLog.objects.create(
                user=request.user,
                action='BIOMETRIC_INTEGRITY_CHECK',
                resource_type='BiometricData',
                resource_id=str(biometric_data.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Integrity check: {'VALID' if is_valid else 'INVALID'} - {message}"
            )
            
            return Response({
                'is_valid': is_valid,
                'hashes_match': hashes_match,
                'current_hash': current_hash,
                'stored_hash': stored_hash,
                'blockchain_verified': blockchain_result['is_valid'],
                'blockchain_info': {
                    'transaction_hash': biometric_data.transaction_hash,
                    'block_number': biometric_data.block_number,
                    'status': biometric_data.status
                },
                'message': message,
                'checked_at': AuditLog.objects.filter(
                    action='BIOMETRIC_INTEGRITY_CHECK',
                    resource_id=str(biometric_data.id)
                ).latest('timestamp').timestamp.isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Integrity check failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# LIVENESS DETECTION VIEWS
# ============================================================================

class LivenessVerificationView(APIView):
    """
    Verify liveness from video frames.
    
    POST /api/auth/liveness/verify/
    
    Accepts:
    - frames: List of base64-encoded video frames (minimum 5)
    - require_blink: Boolean (default True)
    - require_movement: Boolean (default False)
    
    Returns:
    - is_live: Boolean
    - confidence: Float (0-1)
    - checks: Details of each liveness check
    
    Use this endpoint for anti-spoofing verification before
    accepting biometric data.
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=LivenessVerificationSerializer,
        responses={200: dict},
        description="Verify liveness from video frames for anti-spoofing",
        tags=['Biometric - Liveness']
    )
    def post(self, request):
        serializer = LivenessVerificationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .biometric_utils import (
                frames_from_base64_list,
                perform_liveness_verification
            )
            
            # Decode frames
            frames = frames_from_base64_list(serializer.validated_data['frames'])
            
            # Perform liveness check
            result = perform_liveness_verification(
                frames=frames,
                require_blink=serializer.validated_data.get('require_blink', True),
                require_movement=serializer.validated_data.get('require_movement', False),
                check_photo_attack=True
            )
            
            # Log the attempt
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action='LIVENESS_VERIFICATION',
                resource_type='Liveness',
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Liveness check: {'PASSED' if result['is_live'] else 'FAILED'} (confidence: {result['confidence']:.2f})"
            )
            
            return Response({
                'is_live': result['is_live'],
                'confidence': result['confidence'],
                'checks': result['checks'],
                'message': 'Liveness verified' if result['is_live'] else 'Liveness check failed'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Liveness verification failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FaceMatchWithLivenessView(APIView):
    """
    Verify user's face with liveness detection.
    
    POST /api/auth/liveness/face-match/
    
    Requires authentication. Matches live face against stored biometric data.
    
    Accepts:
    - frames: List of base64-encoded video frames
    - require_blink: Boolean (default True)
    - require_movement: Boolean (default False)
    
    Returns:
    - verified: Boolean (overall verification status)
    - liveness: Liveness check details
    - face_match: Face matching details (matched, distance, score)
    """
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=FaceMatchWithLivenessSerializer,
        responses={200: dict},
        description="Verify authenticated user's face with liveness detection",
        tags=['Biometric - Liveness']
    )
    def post(self, request):
        serializer = FaceMatchWithLivenessSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .biometric_utils import (
                frames_from_base64_list,
                verify_face_with_liveness,
                json_to_encoding
            )
            
            # Get user's stored encoding
            biometric_data = request.user.biometric_data
            stored_encoding = json_to_encoding(biometric_data.face_encoding)
            
            # Decode frames
            frames = frames_from_base64_list(serializer.validated_data['frames'])
            
            # Verify face with liveness
            result = verify_face_with_liveness(
                live_frames=frames,
                stored_encoding=stored_encoding,
                require_blink=serializer.validated_data.get('require_blink', True),
                require_movement=serializer.validated_data.get('require_movement', False)
            )
            
            # Log the attempt
            AuditLog.objects.create(
                user=request.user,
                action='FACE_MATCH_WITH_LIVENESS',
                resource_type='BiometricData',
                resource_id=str(biometric_data.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Face match with liveness: {'VERIFIED' if result['verified'] else 'FAILED'}"
            )
            
            response_status = status.HTTP_200_OK if result['verified'] else status.HTTP_401_UNAUTHORIZED
            
            return Response({
                'verified': result['verified'],
                'liveness': result['liveness'],
                'face_match': result['face_match'],
                'message': 'Identity verified successfully' if result['verified'] else result.get('error', 'Verification failed')
            }, status=response_status)
            
        except Exception as e:
            return Response({
                'error': f'Face verification failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FaceLoginWithLivenessView(APIView):
    """
    Login with face recognition and liveness detection.
    
    POST /api/auth/liveness/face-login/
    
    1:1 face authentication with email and liveness check.
    
    Accepts:
    - email: User's email address
    - frames: List of base64-encoded video frames
    - require_blink: Boolean (default True)
    
    Returns:
    - success: Boolean
    - user: User details (if successful)
    - tokens: JWT access and refresh tokens (if successful)
    - liveness: Liveness check details
    - face_match: Face matching details
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=FaceLoginWithLivenessSerializer,
        responses={200: dict},
        description="Login with face recognition and liveness verification",
        tags=['Biometric - Liveness']
    )
    def post(self, request):
        serializer = FaceLoginWithLivenessSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .biometric_utils import (
                frames_from_base64_list,
                verify_face_with_liveness,
                json_to_encoding
            )
            
            # Get user
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            biometric_data = user.biometric_data
            
            # Decode frames
            frames = frames_from_base64_list(serializer.validated_data['frames'])
            
            # Get stored encoding
            stored_encoding = json_to_encoding(biometric_data.face_encoding)
            
            # Verify face with liveness
            result = verify_face_with_liveness(
                live_frames=frames,
                stored_encoding=stored_encoding,
                require_blink=serializer.validated_data.get('require_blink', True),
                require_movement=False
            )
            
            if result['verified']:
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                
                # Update login timestamp
                biometric_data.last_face_login = __import__('django.utils.timezone', fromlist=['now']).now()
                biometric_data.face_login_count = (biometric_data.face_login_count or 0) + 1
                biometric_data.save(update_fields=['last_face_login', 'face_login_count'])
                
                # Log successful login
                AuditLog.objects.create(
                    user=user,
                    action='FACE_LOGIN_WITH_LIVENESS',
                    resource_type='User',
                    resource_id=str(user.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details='Successful face login with liveness verification'
                )
                
                return Response({
                    'success': True,
                    'message': 'Login successful with liveness verification',
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
                    },
                    'liveness': result['liveness'],
                    'face_match': result['face_match']
                }, status=status.HTTP_200_OK)
            else:
                # Log failed attempt
                AuditLog.objects.create(
                    user=user,
                    action='FACE_LOGIN_WITH_LIVENESS_FAILED',
                    resource_type='User',
                    resource_id=str(user.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f"Failed face login: {result.get('error', 'Unknown error')}"
                )
                
                return Response({
                    'success': False,
                    'message': result.get('error', 'Face verification failed'),
                    'liveness': result['liveness'],
                    'face_match': result['face_match']
                }, status=status.HTTP_401_UNAUTHORIZED)
            
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Login failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IDMatchWithLivenessView(APIView):
    """
    Match live face to ID card photo with liveness detection.
    
    POST /api/auth/liveness/id-match/
    
    Used during registration to verify live person matches ID photo.
    
    Accepts:
    - id_card_image: ID card image file
    - frames: List of base64-encoded video frames
    - require_blink: Boolean (default True)
    - require_movement: Boolean (default False)
    
    Returns:
    - verified: Boolean
    - id_face_detected: Boolean
    - liveness: Liveness check details
    - face_match: Face matching details (matched, distance, score)
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=IDMatchWithLivenessSerializer,
        responses={200: dict},
        description="Match live face to ID card photo with liveness detection",
        tags=['Biometric - Liveness']
    )
    def post(self, request):
        serializer = IDMatchWithLivenessSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .biometric_utils import (
                frames_from_base64_list,
                match_face_to_id_with_liveness,
                load_image_from_file
            )
            import cv2
            import numpy as np
            
            # Load ID card image
            id_card_file = serializer.validated_data['id_card_image']
            
            # Read image file to numpy array
            file_bytes = np.frombuffer(id_card_file.read(), np.uint8)
            id_card_image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            if id_card_image is None:
                return Response({
                    'error': 'Failed to decode ID card image'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Decode live frames
            frames = frames_from_base64_list(serializer.validated_data['frames'])
            
            # Match face to ID with liveness
            result = match_face_to_id_with_liveness(
                live_frames=frames,
                id_card_image=id_card_image,
                require_blink=serializer.validated_data.get('require_blink', True),
                require_movement=serializer.validated_data.get('require_movement', False)
            )
            
            # Log the attempt
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action='ID_MATCH_WITH_LIVENESS',
                resource_type='IDVerification',
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"ID match with liveness: {'VERIFIED' if result['verified'] else 'FAILED'}"
            )
            
            response_status = status.HTTP_200_OK if result['verified'] else status.HTTP_400_BAD_REQUEST
            
            return Response({
                'verified': result['verified'],
                'id_face_detected': result['id_face_detected'],
                'liveness': result['liveness'],
                'face_match': result['face_match'],
                'message': 'ID verification successful' if result['verified'] else result.get('error', 'ID verification failed')
            }, status=response_status)
            
        except Exception as e:
            return Response({
                'error': f'ID verification failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Biometric'],
    summary='Preview Face Detection',
    description='''
    Preview face detection with visual feedback (bounding box).
    
    **Use this endpoint to:**
    - Provide real-time feedback during face capture
    - Verify face is properly detected before submission
    - Guide users to position their face correctly
    
    **Returns:**
    - face_detected: Boolean indicating if face was found
    - face_count: Number of faces detected
    - annotated_image: Base64-encoded image with bounding box (if face detected)
    - face_location: Coordinates of detected face
    - quality_issues: List of any quality problems detected
    - message: User-friendly guidance message
    ''',
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'image': {'type': 'string', 'format': 'binary'}
            },
            'required': ['image']
        }
    },
    responses={
        200: {
            'description': 'Face detection completed',
            'content': {
                'application/json': {
                    'example': {
                        'face_detected': True,
                        'face_count': 1,
                        'message': 'Face detected successfully',
                        'annotated_image': 'data:image/jpeg;base64,...',
                        'face_location': {
                            'top': 100,
                            'right': 300,
                            'bottom': 400,
                            'left': 200
                        },
                        'quality_issues': []
                    }
                }
            }
        },
        400: {'description': 'Invalid image or processing failed'}
    }
)
class FaceDetectionPreviewView(APIView):
    """
    Preview face detection with bounding box visualization.
    
    POST /api/biometric/preview-face-detection/
    
    Accepts:
    - image: Face image file
    
    Returns:
    - Face detection status
    - Annotated image with bounding box
    - Quality assessment
    - User guidance
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        import base64
        from io import BytesIO
        
        if 'image' not in request.data:
            return Response({
                'error': 'Image is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .biometric_utils import (
                load_image_from_file,
                draw_face_bounding_box,
                validate_face_quality,
                get_confidence_level
            )
            import face_recognition
            import cv2
            
            # Load image
            image = load_image_from_file(request.data['image'])
            
            # Detect faces
            face_locations = face_recognition.face_locations(image)
            face_count = len(face_locations)
            
            # No face detected
            if face_count == 0:
                return Response({
                    'face_detected': False,
                    'face_count': 0,
                    'message': 'No face detected. Please ensure your face is clearly visible and well-lit.',
                    'guidance': [
                        'Move closer to the camera',
                        'Ensure good lighting on your face',
                        'Remove any obstructions (sunglasses, mask, etc.)',
                        'Look directly at the camera'
                    ]
                }, status=status.HTTP_200_OK)
            
            # Multiple faces detected
            if face_count > 1:
                # Draw boxes around all faces
                annotated_image = image.copy()
                for i, face_loc in enumerate(face_locations):
                    annotated_image = draw_face_bounding_box(
                        annotated_image,
                        face_loc,
                        label=f"Face {i+1}",
                        color=(255, 0, 0)  # Red for multiple faces
                    )
                
                # Convert to base64
                _, buffer = cv2.imencode('.jpg', cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                
                return Response({
                    'face_detected': False,
                    'face_count': face_count,
                    'message': f'Multiple faces detected ({face_count}). Please ensure only one face is visible.',
                    'annotated_image': f'data:image/jpeg;base64,{img_base64}',
                    'guidance': [
                        'Ensure you are alone in the frame',
                        'Remove other people from the background',
                        'Avoid reflections or photos in the background'
                    ]
                }, status=status.HTTP_200_OK)
            
            # Single face detected - validate quality
            top, right, bottom, left = face_locations[0]
            
            # Check face quality
            is_valid, quality_issues = validate_face_quality(
                request.data['image'],
                blur_threshold=30  # Lenient threshold for mobile cameras
            )
            
            # Draw bounding box
            color = (0, 255, 0) if is_valid else (255, 165, 0)  # Green if valid, orange if issues
            label = "Face Detected" if is_valid else "Face Detected (Quality Issues)"
            annotated_image = draw_face_bounding_box(
                image,
                face_locations[0],
                label=label,
                color=color
            )
            
            # Convert to base64
            _, buffer = cv2.imencode('.jpg', cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Prepare guidance based on quality issues
            guidance = []
            if not is_valid:
                for issue in quality_issues:
                    if 'blurry' in issue.lower():
                        guidance.append('Hold the camera steady')
                        guidance.append('Ensure the image is in focus')
                    elif 'dark' in issue.lower():
                        guidance.append('Increase lighting on your face')
                        guidance.append('Move to a brighter location')
                    elif 'bright' in issue.lower():
                        guidance.append('Reduce direct lighting')
                        guidance.append('Avoid bright backgrounds')
                    elif 'small' in issue.lower():
                        guidance.append('Move closer to the camera')
                        guidance.append('Ensure your face fills more of the frame')
            else:
                guidance = ['Face quality is good', 'You can proceed with capture']
            
            return Response({
                'face_detected': True,
                'face_count': 1,
                'message': 'Face detected successfully' if is_valid else 'Face detected but quality could be improved',
                'annotated_image': f'data:image/jpeg;base64,{img_base64}',
                'face_location': {
                    'top': int(top),
                    'right': int(right),
                    'bottom': int(bottom),
                    'left': int(left)
                },
                'quality_valid': is_valid,
                'quality_issues': quality_issues,
                'guidance': guidance
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Face detection failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
