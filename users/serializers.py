from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import Department, DoctorSchedule, ScheduleException, Appointment, Notification

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
        """Validate role - users can only self-register as PATIENT"""
        # Only PATIENT role is allowed for self-registration
        # Staff roles (ADMIN, RECEPTIONIST, NURSE, DOCTOR) must be created by admin
        if value and value in ['ADMIN', 'RECEPTIONIST', 'NURSE', 'DOCTOR']:
            raise serializers.ValidationError(
                "You can only register as a PATIENT. Staff accounts must be created by an administrator."
            )
        return value
    
    def create(self, validated_data):
        """Create user"""
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        # Ensure regular users get PATIENT role
        if 'role' not in validated_data:
            validated_data['role'] = 'PATIENT'
        
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
            'role', 'is_active',
            'department', 'employee_id', 'license_number', 'specialization',
            'date_of_birth', 'age', 'gender', 'phone_number',
            'address_line1', 'address_line2', 'city', 'state_province',
            'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relationship',
            'date_joined', 'last_login'
        )
        read_only_fields = (
            'id', 'role', 'is_active', 'date_joined', 'last_login'
        )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_age(self, obj):
        return obj.age


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
            'role', 'is_active', 'is_staff', 'is_superuser',
            'date_of_birth', 'age', 'gender', 'phone_number',
            'address_line1', 'address_line2', 'city', 'state_province',
            'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relationship',
            'date_joined', 'last_login'
        )
        read_only_fields = ('id', 'date_joined', 'last_login')
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_age(self, obj):
        return obj.age





class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Hospital Departments"""
    staff_count = serializers.IntegerField(source='staff_members.count', read_only=True)
    
    class Meta:
        model = Department
        fields = ('id', 'name', 'code', 'description', 'is_active', 'staff_count')


class DoctorScheduleSerializer(serializers.ModelSerializer):
    """Serializer for Doctor Schedules"""
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = DoctorSchedule
        fields = (
            'id', 'doctor', 'doctor_name', 'day_of_week', 'day_name',
            'start_time', 'end_time', 'slot_duration_minutes',
            'max_patients_per_slot', 'is_active'
        )


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for Appointments"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    booked_by_name = serializers.CharField(source='booked_by.get_full_name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Appointment
        fields = (
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'booked_by', 'booked_by_name',
            'appointment_date', 'appointment_time',
            'appointment_type', 'status', 'status_display',
            'reason', 'created_at', 'checked_in_at', 'completed_at'
        )
        read_only_fields = ('booked_by', 'created_at', 'checked_in_at', 'completed_at')


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notifications"""
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = (
            'id', 'recipient', 'notification_type', 'type_display',
            'priority', 'title', 'message', 'related_appointment',
            'is_read', 'created_at'
        )
        read_only_fields = ('recipient', 'created_at')
