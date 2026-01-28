from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user"""
        if not email:
            raise ValueError('Users must have an email address')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'ADMIN')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class Department(models.Model):
    """Hospital departments (e.g., Cardiology, Radiology, etc.)"""
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="Short code for the department")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
    
    def __str__(self):
        return self.name


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with email as username and role-based access"""
    
    ROLE_CHOICES = (
        ('ADMIN', 'Administrator'),
        ('RECEPTIONIST', 'Medical Receptionist'),
        ('NURSE', 'Nurse'),
        ('DOCTOR', 'Doctor'),
        ('PATIENT', 'Patient'),
    )
    
    ACCOUNT_STATUS_CHOICES = (
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    KYC_STATUS_CHOICES = (
        ('NOT_STARTED', 'Not Started'),
        ('PENDING', 'Pending Verification'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
    )
    
    # Basic fields
    email = models.EmailField(unique=True, max_length=255)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    # Demographic Information
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=20,
        choices=[
            ('MALE', 'Male'),
            ('FEMALE', 'Female'),
            ('OTHER', 'Other'),
            ('PREFER_NOT_TO_SAY', 'Prefer not to say')
        ],
        blank=True
    )
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Address Information
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True, default='Philippines')
    
    # Emergency Contact (primarily for patients)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=100, blank=True)
    
    # Role and permissions
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='PATIENT')
    
    # Account status (primarily for patients)
    account_status = models.CharField(
        max_length=20,
        choices=ACCOUNT_STATUS_CHOICES,
        default='APPROVED',
        help_text='Account approval status (for patients)'
    )
    
    # KYC verification status
    kyc_status = models.CharField(
        max_length=20,
        choices=KYC_STATUS_CHOICES,
        default='NOT_STARTED',
        help_text='KYC verification status'
    )
    
    # Temporary ID for patient registration
    temporary_id = models.FileField(
        upload_to='temporary_ids/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text='Temporary ID uploaded during registration'
    )
    
    # Department assignment (for staff members: receptionist, nurse, doctor)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members',
        help_text='Department this staff member belongs to'
    )
    
    # Professional Information (for doctors and nurses)
    employee_id = models.CharField(max_length=50, blank=True, help_text='Employee ID number')
    license_number = models.CharField(max_length=100, blank=True, help_text='Professional license number')
    specialization = models.CharField(max_length=200, blank=True, help_text='Medical specialization (for doctors)')
    
    # Status fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['role', 'account_status'], name='idx_role_account_status'),
            models.Index(fields=['account_status'], name='idx_account_status'),
            models.Index(fields=['kyc_status'], name='idx_kyc_status'),
            models.Index(fields=['email'], name='idx_email'),
        ]
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return the short name for the user"""
        return self.first_name or self.email
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def get_full_address(self):
        """Return formatted full address"""
        parts = [self.address_line1, self.address_line2, self.city, self.state_province, self.postal_code, self.country]
        return ", ".join([p for p in parts if p])


class DoctorSchedule(models.Model):
    """Recurring weekly schedule for doctors"""
    
    DAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )
    
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedules', limit_choices_to={'role': 'DOCTOR'})
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.IntegerField(default=30)
    max_patients_per_slot = models.IntegerField(
        default=1,
        help_text='Maximum number of patients per time slot'
    )
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('doctor', 'day_of_week')
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.doctor.get_full_name()} - {self.get_day_of_week_display()}"


class ScheduleException(models.Model):
    """One-time exceptions to a doctor's schedule (e.g., leaves, extra shifts)"""
    
    EXCEPTION_TYPES = (
        ('OFF_DUTY', 'Off Duty / Leave'),
        ('EXTRA_SHIFT', 'Extra Shift'),
    )
    
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedule_exceptions', limit_choices_to={'role': 'DOCTOR'})
    exception_type = models.CharField(max_length=20, choices=EXCEPTION_TYPES)
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"{self.doctor.get_full_name()} - {self.exception_type} on {self.date}"


class Appointment(models.Model):
    """Patient appointments with doctors"""
    
    STATUS_CHOICES = (
        ('SCHEDULED', 'Scheduled'),
        ('CHECKED_IN', 'Checked In'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
    )
    
    APPOINTMENT_TYPES = (
        ('GENERAL', 'General Consultation'),
        ('FOLLOW_UP', 'Follow-up Visit'),
        ('EMERGENCY', 'Emergency'),
        ('PROCEDURE', 'Medical Procedure'),
        ('VACCINATION', 'Vaccination'),
    )
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments', limit_choices_to={'role': 'PATIENT'})
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_appointments', limit_choices_to={'role': 'DOCTOR'})
    booked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='appointments_booked')
    
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPES, default='GENERAL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    reason = models.TextField(blank=True)
    
    # Timing audit
    checked_in_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-appointment_date', '-appointment_time']
        indexes = [
            models.Index(fields=['appointment_date', 'appointment_time']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.patient.get_full_name()} with Dr. {self.doctor.last_name} on {self.appointment_date}"


class Notification(models.Model):
    """System notifications for staff and patients"""
    
    TYPES = (
        ('NEW_APPOINTMENT', 'New Appointment Scheduled'),
        ('PATIENT_CHECK_IN', 'Patient Arrived / Checked In'),
        ('APPOINTMENT_CANCELLED', 'Appointment Cancelled'),
        ('RECORD_UPLOADED', 'New Medical Record Uploaded'),
        ('SYSTEM_ALERT', 'System Alert'),
    )
    
    PRIORITIES = (
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITIES, default='NORMAL')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    
    # Optional relation to other objects
    related_appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.recipient.email}: {self.title}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()


class DoctorNurseAssignment(models.Model):
    """Assignments between doctors and nurses for shift collaboration"""
    
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_nurses', limit_choices_to={'role': 'DOCTOR'})
    nurse = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_doctors', limit_choices_to={'role': 'NURSE'})
    is_primary = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('doctor', 'nurse')
        verbose_name = 'Doctor-Nurse Assignment'
    
    def __str__(self):
        return f"Dr. {self.doctor.last_name} / Nurse {self.nurse.last_name}"


class BiometricData(models.Model):
    """
    Biometric data for user identity verification.
    
    Stores ID card information, face encodings, and verification status.
    Integrated with blockchain for tamper-proof audit trail.
    """
    
    ID_CARD_TYPE_CHOICES = (
        ('NATIONAL_ID', 'PhilID / National ID (ePhilID)'),
        ('DRIVERS_LICENSE', "Driver's License"),
        ('PHILHEALTH_ID', 'PhilHealth ID'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending Verification'),
        ('CONFIRMED', 'Confirmed on Blockchain'),
        ('FAILED', 'Blockchain Registration Failed'),
    )
    
    # User relationship
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='biometric_data',
        help_text='User associated with this biometric data'
    )
    
    # ID Card Information
    id_card_image = models.ImageField(
        upload_to='id_cards/%Y/%m/%d/',
        help_text='Uploaded ID card image'
    )
    id_card_type = models.CharField(
        max_length=20,
        choices=ID_CARD_TYPE_CHOICES,
        help_text='Type of Philippine ID'
    )
    id_number = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text='ID number extracted from card'
    )
    id_full_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Full name as shown on ID'
    )
    id_date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text='Date of birth from ID'
    )
    id_address = models.TextField(
        blank=True,
        default='',
        help_text='Address from ID'
    )
    id_face_image = models.ImageField(
        upload_to='id_faces/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text='Face extracted from ID card'
    )
    
    # Live Face Information
    live_face_image = models.ImageField(
        upload_to='live_faces/%Y/%m/%d/',
        help_text='Live selfie for verification'
    )
    
    # Face Encodings (128-dimensional arrays stored as JSON)
    id_face_encoding = models.JSONField(
        null=True,
        blank=True,
        help_text='Face encoding from ID card (128-dim array)'
    )
    live_face_encoding = models.JSONField(
        help_text='Face encoding from live selfie (128-dim array)'
    )
    
    # Verification Results
    face_match_score = models.FloatField(
        help_text='Face matching distance (0-1, lower = better match)'
    )
    face_match_threshold = models.FloatField(
        default=0.6,
        help_text='Threshold used for verification'
    )
    is_face_verified = models.BooleanField(
        default=False,
        help_text='Whether face verification passed'
    )
    face_recognition_enabled = models.BooleanField(
        default=False,
        help_text='Whether user can use face login'
    )
    
    # Blockchain Integration
    biometric_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        default='',
        help_text='Unique identifier for blockchain (BIO_YYYYMMDD_UUID)'
    )
    biometric_hash = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text='SHA-256 hash of biometric data'
    )
    blockchain_address = models.CharField(
        max_length=42,
        blank=True,
        help_text='Ethereum address for blockchain registration'
    )
    transaction_hash = models.CharField(
        max_length=66,
        blank=True,
        help_text='Blockchain transaction hash'
    )
    block_number = models.IntegerField(
        null=True,
        blank=True,
        help_text='Block number where data was registered'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text='Blockchain registration status'
    )
    is_blockchain_verified = models.BooleanField(
        default=False,
        help_text='Whether data is verified on blockchain'
    )
    
    # Audit Trail
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_biometrics',
        help_text='Staff member who verified this data'
    )
    verification_notes = models.TextField(
        blank=True,
        help_text='Notes from manual verification'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Biometric Data'
        verbose_name_plural = 'Biometric Data'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['biometric_id']),
            models.Index(fields=['status']),
            models.Index(fields=['is_face_verified']),
            models.Index(fields=['face_recognition_enabled']),
        ]
    
    def __str__(self):
        return f"Biometric Data for {self.user.email}"
    
    def get_verification_status_display_verbose(self):
        """Get detailed verification status"""
        if self.is_face_verified and self.is_blockchain_verified:
            return "Fully Verified"
        elif self.is_face_verified:
            return "Face Verified (Blockchain Pending)"
        elif self.is_blockchain_verified:
            return "Blockchain Verified (Face Pending)"
        else:
            return "Not Verified"