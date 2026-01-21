from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'first_name', 'last_name', 'role')
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'role': {'required': False}
        }
    
    def validate(self, attrs):
        """Validate that passwords match"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs
    
    def validate_role(self, value):
        """Validate role - users can't register as ADMIN or IT_STAFF"""
        if value and value in ['ADMIN', 'IT_STAFF']:
            raise serializers.ValidationError(
                "You cannot register with ADMIN or IT_STAFF role."
            )
        return value
    
    def create(self, validated_data):
        """Create user"""
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        # Ensure regular users get PATIENT role and PENDING status
        if 'role' not in validated_data:
            validated_data['role'] = 'PATIENT'
        
        # Set account_status to PENDING for patients (requires approval)
        if validated_data.get('role') == 'PATIENT':
            validated_data['account_status'] = 'PENDING'
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True, 
        write_only=True,
        style={'input_type': 'password'}
    )


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details"""
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'account_status', 'kyc_status', 'is_active',
            'date_of_birth', 'age', 'gender', 'phone_number',
            'address_line1', 'address_line2', 'city', 'state_province',
            'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relationship',
            'date_joined', 'last_login'
        )
        read_only_fields = (
            'id', 'role', 'account_status', 'kyc_status', 
            'is_active', 'date_joined', 'last_login'
        )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_age(self, obj):
        return obj.get_age()


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'date_of_birth', 'gender', 
            'phone_number', 'address_line1', 'address_line2', 
            'city', 'state_province', 'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship'
        )
    
    def update(self, instance, validated_data):
        """Update user instance"""
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate that new passwords match"""
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {"new_password": "New password fields didn't match."}
            )
        return attrs
    
    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class UserAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin user management - includes sensitive fields"""
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'account_status', 'kyc_status', 
            'is_active', 'is_staff', 'is_superuser',
            'date_of_birth', 'age', 'gender', 'phone_number',
            'address_line1', 'address_line2', 'city', 'state_province',
            'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relationship',
            'temporary_id',
            'date_joined', 'last_login'
        )
        read_only_fields = ('id', 'date_joined', 'last_login')
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_age(self, obj):
        return obj.get_age()


class AccountStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating account status (Admin only)"""
    
    class Meta:
        model = User
        fields = ('account_status',)
    
    def validate_account_status(self, value):
        """Validate account status"""
        valid_statuses = ['PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        return value