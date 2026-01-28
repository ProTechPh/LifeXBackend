"""
Serializers for biometric authentication endpoints.

Handles validation and serialization for:
- Face image upload and verification
- Biometric registration
- Face recognition login

Note: ID card verification is now handled by Didit.me integration.
      See users/didit_service.py for ID verification.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import BiometricData
from .biometric_utils import (
    detect_and_extract_face,
    generate_face_encoding,
    compare_faces,
    validate_face_quality,
    encoding_to_json,
    get_face_match_threshold,
    BiometricError,
    FaceDetectionError,
    FaceQualityError,
)
from .biometric_blockchain import (
    generate_biometric_id,
    hash_biometric_data,
    register_biometric_on_blockchain,
    get_biometric_blockchain_status
)
from .id_ocr import extract_text_from_id
from .ocr_exceptions import (
    OCRError,
    ImageQualityError,
    IDTypeNotRecognizedError,
    DataExtractionError,
    FaceExtractionError
)

User = get_user_model()


class BiometricDataSerializer(serializers.ModelSerializer):
    """Serializer for BiometricData model"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    blockchain_status = serializers.SerializerMethodField()
    
    class Meta:
        model = BiometricData
        fields = [
            'id', 'user', 'user_email', 'user_full_name',
            'id_card_type', 'id_number', 'id_full_name',
            'id_date_of_birth', 'id_address',
            'face_match_score', 'is_face_verified',
            'face_recognition_enabled', 
            # Blockchain fields
            'biometric_id', 'biometric_hash', 'blockchain_address',
            'transaction_hash', 'block_number', 'status',
            'is_blockchain_verified', 'blockchain_status',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'biometric_id', 'biometric_hash', 'blockchain_address',
            'transaction_hash', 'block_number', 'status', 
            'is_blockchain_verified', 'created_at', 'updated_at'
        ]
    
    def get_user_full_name(self, obj):
        return obj.user.get_full_name()
    
    def get_blockchain_status(self, obj):
        """Get blockchain status information"""
        return get_biometric_blockchain_status(obj)


class IDCardUploadSerializer(serializers.Serializer):
    """Serializer for ID card upload and processing"""
    
    id_card_image = serializers.ImageField(required=True)
    id_card_type = serializers.ChoiceField(
        choices=BiometricData.ID_CARD_TYPE_CHOICES,
        required=True
    )
    
    def validate_id_card_image(self, value):
        """Validate ID card image file"""
        # Check file size
        max_size = settings.BIOMETRIC_SETTINGS.get('MAX_IMAGE_SIZE', 10 * 1024 * 1024)
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image file too large. Maximum size is {max_size / (1024 * 1024):.1f}MB"
            )
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        return value
    
    def process_id_card(self):
        """Process ID card and extract information"""
        id_card_image = self.validated_data['id_card_image']
        
        try:
            # Extract text using OCR
            extracted_data = extract_text_from_id(id_card_image)
            
            # Reset file pointer after reading
            id_card_image.seek(0)
            
            # Detect and extract face from ID
            try:
                face_image, face_location = detect_and_extract_face(id_card_image)
                id_card_image.seek(0)
                
                # Generate face encoding
                id_face_encoding = generate_face_encoding(id_card_image)
                id_card_image.seek(0)
                
                has_face = True
            except FaceDetectionError as e:
                # ID card might not have a clear face photo
                has_face = False
                id_face_encoding = None
                face_location = None
            
            return {
                'extracted_text': extracted_data,
                'has_face': has_face,
                'face_encoding': encoding_to_json(id_face_encoding) if has_face else None,
                'face_location': face_location
            }
            
        except OCRError as e:
            raise serializers.ValidationError(f"OCR processing failed: {str(e)}")
        except BiometricError as e:
            raise serializers.ValidationError(f"ID card processing failed: {str(e)}")


class LiveFaceUploadSerializer(serializers.Serializer):
    """Serializer for live face photo upload"""
    
    live_face_image = serializers.ImageField(required=True)
    
    def validate_live_face_image(self, value):
        """Validate live face image"""
        # Check file size
        max_size = settings.BIOMETRIC_SETTINGS.get('MAX_IMAGE_SIZE', 10 * 1024 * 1024)
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image file too large. Maximum size is {max_size / (1024 * 1024):.1f}MB"
            )
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Validate face quality with lenient threshold for login (50 instead of 100)
        # Login validation can be more lenient since we're comparing against stored encoding
        try:
            is_valid, issues = validate_face_quality(value, blur_threshold=50.0)
            value.seek(0)
            
            if not is_valid:
                raise serializers.ValidationError(
                    f"Face quality issues: {', '.join(issues)}"
                )
        except Exception as e:
            raise serializers.ValidationError(f"Face validation failed: {str(e)}")
        
        return value
    
    def process_live_face(self):
        """Process live face image and generate encoding"""
        live_face_image = self.validated_data['live_face_image']
        
        try:
            # Generate face encoding
            face_encoding = generate_face_encoding(live_face_image)
            live_face_image.seek(0)
            
            return {
                'face_encoding': encoding_to_json(face_encoding)
            }
            
        except FaceDetectionError as e:
            raise serializers.ValidationError(f"Face detection failed: {str(e)}")
        except BiometricError as e:
            raise serializers.ValidationError(f"Face processing failed: {str(e)}")


class BiometricRegistrationSerializer(serializers.Serializer):
    """Serializer for complete biometric registration"""
    
    # User information
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    password2 = serializers.CharField(write_only=True, required=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    
    # Biometric data
    id_card_image = serializers.ImageField(required=True)
    id_card_type = serializers.ChoiceField(
        choices=BiometricData.ID_CARD_TYPE_CHOICES,
        required=True
    )
    live_face_image = serializers.ImageField(required=True)
    
    def validate_email(self, value):
        """Check if email already exists"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value
    
    def validate(self, data):
        """Validate passwords match"""
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password2": "Passwords do not match"})
        return data
    
    def validate_id_card_image(self, value):
        """Validate ID card image"""
        max_size = settings.BIOMETRIC_SETTINGS.get('MAX_IMAGE_SIZE', 10 * 1024 * 1024)
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image file too large. Maximum size is {max_size / (1024 * 1024):.1f}MB"
            )
        return value
    
    def validate_live_face_image(self, value):
        """Validate live face image with lenient threshold for registration"""
        max_size = settings.BIOMETRIC_SETTINGS.get('MAX_IMAGE_SIZE', 10 * 1024 * 1024)
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image file too large. Maximum size is {max_size / (1024 * 1024):.1f}MB"
            )
        
        # Validate face quality with lenient threshold for registration (70 instead of 100)
        # This allows users to register while still recording quality issues for security monitoring
        try:
            is_valid, issues = validate_face_quality(value, blur_threshold=70.0)
            value.seek(0)
            
            if not is_valid:
                raise serializers.ValidationError(
                    f"Face quality issues: {', '.join(issues)}"
                )
        except Exception as e:
            raise serializers.ValidationError(f"Face validation failed: {str(e)}")
        
        return value
    
    def create(self, validated_data):
        """Create user with biometric data"""
        # Extract biometric data
        id_card_image = validated_data.pop('id_card_image')
        id_card_type = validated_data.pop('id_card_type')
        live_face_image = validated_data.pop('live_face_image')
        password2 = validated_data.pop('password2')
        
        try:
            # Process ID card with user-selected ID type
            id_extracted_data = extract_text_from_id(id_card_image, id_type=id_card_type)
            id_card_image.seek(0)
            
            # Try to extract face from ID
            try:
                id_face_encoding = generate_face_encoding(id_card_image)
                id_card_image.seek(0)
                has_id_face = True
            except FaceDetectionError:
                id_face_encoding = None
                has_id_face = False
            
            # Process live face
            live_face_encoding = generate_face_encoding(live_face_image)
            live_face_image.seek(0)
            
            # Compare faces if ID has a face
            if has_id_face:
                threshold = get_face_match_threshold()
                is_match, distance = compare_faces(
                    id_face_encoding, 
                    live_face_encoding, 
                    tolerance=threshold
                )
                
                if not is_match:
                    raise serializers.ValidationError({
                        'face_match': f'Face does not match ID card. Confidence score: {distance:.3f} (threshold: {threshold})'
                    })
            else:
                # No face in ID, just verify live face is valid
                is_match = True
                distance = 0.0
            
            # Generate unique biometric ID
            biometric_id = generate_biometric_id()
            
            # Hash biometric data (ID card + face encodings)
            biometric_hash = hash_biometric_data(
                id_card_image,
                live_face_image,
                encoding_to_json(id_face_encoding) if has_id_face else None,
                encoding_to_json(live_face_encoding)
            )
            
            # Create user
            user = User.objects.create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
                role='PATIENT'
            )
            
            # Create biometric data with blockchain fields
            # Auto-enable face recognition if face is verified
            biometric_data = BiometricData.objects.create(
                user=user,
                id_card_image=id_card_image,
                id_card_type=id_card_type,
                id_number=id_extracted_data.get('id_number', ''),
                id_full_name=id_extracted_data.get('name', ''),
                id_address=id_extracted_data.get('address', ''),
                live_face_image=live_face_image,
                live_face_encoding=encoding_to_json(live_face_encoding),
                id_face_encoding=encoding_to_json(id_face_encoding) if has_id_face else None,
                face_match_score=distance,
                face_match_threshold=get_face_match_threshold(),
                is_face_verified=is_match,
                face_recognition_enabled=is_match,  # Auto-enable if face verified
                # Blockchain fields
                biometric_id=biometric_id,
                biometric_hash=biometric_hash,
                status='PENDING'
            )
            
            # Register on blockchain
            try:
                blockchain_result = register_biometric_on_blockchain(user, biometric_data)
                # biometric_data is updated by register_biometric_on_blockchain
            except Exception as e:
                # Blockchain registration failed, but user is still created
                # Status is already set to FAILED by register_biometric_on_blockchain
                pass
            
            return user
            
        except FaceDetectionError as e:
            raise serializers.ValidationError(f"Face detection failed: {str(e)}")
        except BiometricError as e:
            raise serializers.ValidationError(f"Biometric processing failed: {str(e)}")


class FaceLoginSerializer(serializers.Serializer):
    """Serializer for face recognition login"""
    
    email = serializers.EmailField(required=True)
    face_image = serializers.ImageField(required=True)
    
    def validate_face_image(self, value):
        """Validate face image"""
        max_size = settings.BIOMETRIC_SETTINGS.get('MAX_IMAGE_SIZE', 10 * 1024 * 1024)
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image file too large. Maximum size is {max_size / (1024 * 1024):.1f}MB"
            )
        return value
    
    def validate(self, data):
        """Validate face matches stored biometric data"""
        email = data['email']
        face_image = data['face_image']
        
        try:
            # Get user
            user = User.objects.get(email=email)
            
            # Check if user has biometric data
            if not hasattr(user, 'biometric_data'):
                raise serializers.ValidationError({
                    'email': 'Face recognition not set up for this account'
                })
            
            biometric_data = user.biometric_data
            
            # Check if face recognition is enabled
            if not biometric_data.face_recognition_enabled:
                raise serializers.ValidationError({
                    'email': 'Face recognition login is not enabled for this account'
                })
            
            # Generate face encoding from submitted image
            try:
                submitted_encoding = generate_face_encoding(face_image)
                face_image.seek(0)
            except FaceDetectionError as e:
                raise serializers.ValidationError({
                    'face_image': f'Face detection failed: {str(e)}'
                })
            
            # Compare with stored encoding
            stored_encoding = biometric_data.live_face_encoding
            threshold = get_face_match_threshold()
            
            is_match, distance = compare_faces(
                stored_encoding,
                submitted_encoding,
                tolerance=threshold
            )
            
            if not is_match:
                raise serializers.ValidationError({
                    'face_image': f'Face does not match. Please try again or use password login.'
                })
            
            # Store user in validated data for view to use
            data['user'] = user
            data['match_score'] = distance
            
            return data
            
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'email': 'User with this email does not exist'
            })
        except BiometricError as e:
            raise serializers.ValidationError({
                'face_image': f'Face processing failed: {str(e)}'
            })


class ToggleFaceRecognitionSerializer(serializers.Serializer):
    """Serializer for enabling/disabling face recognition"""
    
    enable = serializers.BooleanField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    
    def validate_password(self, value):
        """Verify user's password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Invalid password")
        return value
    
    def validate(self, data):
        """Validate user has biometric data"""
        user = self.context['request'].user
        
        if not hasattr(user, 'biometric_data'):
            raise serializers.ValidationError({
                'enable': 'Biometric data not found. Please complete biometric registration first.'
            })
        
        biometric_data = user.biometric_data
        
        if data['enable'] and not biometric_data.is_face_verified:
            raise serializers.ValidationError({
                'enable': 'Face verification not completed. Cannot enable face recognition.'
            })
        
        return data


class BiometricVerificationSerializer(serializers.Serializer):
    """Serializer for staff to verify biometric data"""
    
    approved = serializers.BooleanField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        """Update biometric verification status"""
        instance.is_face_verified = validated_data['approved']
        instance.verification_notes = validated_data.get('notes', '')
        instance.verified_by = self.context['request'].user
        instance.save()
        
        return instance


# ============================================================================
# LIVENESS DETECTION SERIALIZERS
# ============================================================================

class LivenessVerificationSerializer(serializers.Serializer):
    """
    Serializer for liveness verification endpoint.
    
    Accepts a list of base64-encoded video frames for liveness checking.
    """
    
    frames = serializers.ListField(
        child=serializers.CharField(),
        min_length=5,
        max_length=60,
        help_text='List of base64-encoded video frames (minimum 5 frames)'
    )
    require_blink = serializers.BooleanField(
        default=True,
        help_text='Require blink detection to pass'
    )
    require_movement = serializers.BooleanField(
        default=False,
        help_text='Require head movement detection to pass'
    )
    
    def validate_frames(self, value):
        """Validate that frames are valid base64 images"""
        if len(value) < 5:
            raise serializers.ValidationError(
                "At least 5 frames are required for liveness detection"
            )
        
        # Check first frame is valid base64
        try:
            import base64
            first_frame = value[0]
            if ',' in first_frame:
                first_frame = first_frame.split(',')[1]
            base64.b64decode(first_frame)
        except Exception:
            raise serializers.ValidationError(
                "Invalid base64 encoding for frames"
            )
        
        return value


class FaceMatchWithLivenessSerializer(serializers.Serializer):
    """
    Serializer for face matching with liveness verification.
    
    Used for authenticated users to verify their identity.
    """
    
    frames = serializers.ListField(
        child=serializers.CharField(),
        min_length=5,
        max_length=60,
        help_text='List of base64-encoded video frames'
    )
    require_blink = serializers.BooleanField(
        default=True,
        help_text='Require blink detection'
    )
    require_movement = serializers.BooleanField(
        default=False,
        help_text='Require head movement detection'
    )
    
    def validate(self, data):
        """Validate user has biometric data"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if not hasattr(request.user, 'biometric_data'):
                raise serializers.ValidationError(
                    "No biometric data found. Please complete biometric registration."
                )
            if not request.user.biometric_data.face_encoding:
                raise serializers.ValidationError(
                    "No face encoding stored. Please complete biometric registration."
                )
        return data


class FaceLoginWithLivenessSerializer(serializers.Serializer):
    """
    Serializer for face login with liveness verification.
    
    Used for 1:1 face authentication with email.
    """
    
    email = serializers.EmailField(
        required=True,
        help_text='User email address'
    )
    frames = serializers.ListField(
        child=serializers.CharField(),
        min_length=5,
        max_length=60,
        help_text='List of base64-encoded video frames'
    )
    require_blink = serializers.BooleanField(
        default=True,
        help_text='Require blink detection'
    )
    
    def validate_email(self, value):
        """Validate user exists and has face recognition enabled"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        
        if not hasattr(user, 'biometric_data'):
            raise serializers.ValidationError(
                "User has not completed biometric registration"
            )
        
        if not user.biometric_data.face_recognition_enabled:
            raise serializers.ValidationError(
                "Face recognition is not enabled for this user"
            )
        
        if not user.biometric_data.face_encoding:
            raise serializers.ValidationError(
                "No face data stored for this user"
            )
        
        return value


class IDMatchWithLivenessSerializer(serializers.Serializer):
    """
    Serializer for ID card matching with liveness verification.
    
    Used during registration to verify live person matches ID photo.
    """
    
    id_card_image = serializers.ImageField(
        required=True,
        help_text='ID card image file'
    )
    frames = serializers.ListField(
        child=serializers.CharField(),
        min_length=5,
        max_length=60,
        help_text='List of base64-encoded video frames from live capture'
    )
    require_blink = serializers.BooleanField(
        default=True,
        help_text='Require blink detection'
    )
    require_movement = serializers.BooleanField(
        default=False,
        help_text='Require head movement detection'
    )
    
    def validate_id_card_image(self, value):
        """Validate ID card image"""
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image file too large. Maximum size is 10MB"
            )
        
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed: JPEG, PNG"
            )
        
        return value
