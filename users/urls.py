from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView,
    UserLoginView,
    UserLogoutView,
    UserProfileView,
    ChangePasswordView,
    UserListView,
    UserAdminView,
)
from .staff_views import (
    DepartmentListView,
    DoctorByDepartmentListView,
    DoctorListView,
    DoctorScheduleListView,
    AppointmentCreateView,
    AppointmentListView,
    CheckInPatientView,
    CompleteAppointmentView,
    CancelAppointmentView,
    UpdateAppointmentView,
    NotificationListView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
    NotificationDeleteView,
    NotificationStatsView,
    DoctorDashboardStatsView,
    AdminSystemStatsView,
    NurseDashboardStatsView,
    ReceptionistDashboardStatsView,
)
from .biometric_views import (
    BiometricRegistrationView,
    IDCardUploadView,
    FaceMatchVerificationView,
    FaceLoginView,
    FaceRecognitionStatusView,
    ToggleFaceRecognitionView,
    BiometricDataDetailView,
    PendingBiometricVerificationsView,
    VerifyBiometricDataView,
    CheckBiometricIntegrityView,
    # Liveness detection views
    LivenessVerificationView,
    FaceMatchWithLivenessView,
    FaceLoginWithLivenessView,
    IDMatchWithLivenessView,
)
from .quick_face_login_views import (
    QuickFaceLoginView,
    ConfirmFaceLoginView,
    IdentifyFaceView,
    ConfirmIdentityView,
    FaceLoginStatsView,
)

app_name = 'users'

urlpatterns = [
    # Authentication
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Biometric Registration & Verification
    path('biometric/register/', BiometricRegistrationView.as_view(), name='biometric_register'),
    path('biometric/upload-id/', IDCardUploadView.as_view(), name='upload_id'),
    path('biometric/verify-face/', FaceMatchVerificationView.as_view(), name='verify_face'),
    path('biometric/detail/', BiometricDataDetailView.as_view(), name='biometric_detail'),
    
    # Face Login (1:1 with email)
    path('login-with-face/', FaceLoginView.as_view(), name='face_login'),
    
    # Face-Only Login (1:N without email)
    path('quick-face-login/', QuickFaceLoginView.as_view(), name='quick_face_login'),
    path('confirm-face-login/', ConfirmFaceLoginView.as_view(), name='confirm_face_login'),
    path('identify-face/', IdentifyFaceView.as_view(), name='identify_face'),
    path('confirm-identity/', ConfirmIdentityView.as_view(), name='confirm_identity'),
    path('face-login-stats/', FaceLoginStatsView.as_view(), name='face_login_stats'),
    
    # Biometric Management
    path('biometric/status/', FaceRecognitionStatusView.as_view(), name='face_recognition_status'),
    path('biometric/toggle/', ToggleFaceRecognitionView.as_view(), name='toggle_face_recognition'),
    
    # Liveness Detection (Anti-Spoofing)
    path('liveness/verify/', LivenessVerificationView.as_view(), name='liveness_verify'),
    path('liveness/face-match/', FaceMatchWithLivenessView.as_view(), name='face_match_with_liveness'),
    path('liveness/face-login/', FaceLoginWithLivenessView.as_view(), name='face_login_with_liveness'),
    path('liveness/id-match/', IDMatchWithLivenessView.as_view(), name='id_match_with_liveness'),
    
    # Admin: Biometric Verification
    path('biometric/pending/', PendingBiometricVerificationsView.as_view(), name='pending_biometrics'),
    path('biometric/verify/<int:biometric_id>/', VerifyBiometricDataView.as_view(), name='verify_biometric'),
    path('biometric/check-integrity/<int:biometric_id>/', CheckBiometricIntegrityView.as_view(), name='check_biometric_integrity'),
    
    # User Profile
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # User Management (Admin)
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', UserAdminView.as_view(), name='user_admin_detail'),
    
    # Hospital structure (Receptionist)
    path('departments/', DepartmentListView.as_view(), name='department_list'),
    path('departments/<int:dept_id>/doctors/', DoctorByDepartmentListView.as_view(), name='doctor_list_by_dept'),
    path('staff/doctors/', DoctorListView.as_view(), name='doctor_list'),
    
    # Schedules and Appointments (Receptionist/Doctor/Patient)
    path('doctors/<int:doctor_id>/schedule/', DoctorScheduleListView.as_view(), name='doctor_schedule'),
    path('appointments/', AppointmentListView.as_view(), name='appointment_list'),
    path('appointments/create/', AppointmentCreateView.as_view(), name='appointment_create'),
    path('appointments/<int:pk>/', UpdateAppointmentView.as_view(), name='appointment_update'),
    path('appointments/<int:appointment_id>/check-in/', CheckInPatientView.as_view(), name='check_in_patient'),
    path('appointments/<int:appointment_id>/complete/', CompleteAppointmentView.as_view(), name='complete_appointment'),
    path('appointments/<int:appointment_id>/cancel/', CancelAppointmentView.as_view(), name='cancel_appointment'),
    
    # Notifications (Primary for Doctors)
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/stats/', NotificationStatsView.as_view(), name='notification_stats'),
    path('notifications/mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
    path('notifications/<int:notification_id>/read/', NotificationMarkReadView.as_view(), name='notification_read'),
    path('notifications/<int:notification_id>/', NotificationDeleteView.as_view(), name='notification_delete'),
    
    # Dashboard Statistics
    path('dashboard/doctor-stats/', DoctorDashboardStatsView.as_view(), name='doctor_dashboard_stats'),
    path('dashboard/system-stats/', AdminSystemStatsView.as_view(), name='admin_system_stats'),
    path('dashboard/nurse-stats/', NurseDashboardStatsView.as_view(), name='nurse_dashboard_stats'),
    path('dashboard/receptionist-stats/', ReceptionistDashboardStatsView.as_view(), name='receptionist_dashboard_stats'),
]