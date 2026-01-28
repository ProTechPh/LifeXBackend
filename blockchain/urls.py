from django.urls import path
from .medical_views import (
    PatientRegistrationView,
    PatientListView,
    UploadMedicalRecordView,
    PatientRecordsView,
    MyMedicalRecordsView,
    MyMedicalRecordDetailView,
    VerifyMyRecordView,
    SystemStatsView,
    AuditLogView,
    DownloadMedicalRecordView,
    PendingPatientsView,
    ApprovePatientView,
    RejectPatientView,
    PendingRecordsView,
    EditMedicalRecordView,
    ApproveMedicalRecordView,
    RejectMedicalRecordView,
    UserActivityView,
    SystemActivityView,
)

app_name = 'blockchain'

urlpatterns = [
    # STAFF endpoints
    path('staff/register-patient/', PatientRegistrationView.as_view(), name='register_patient'),
    path('staff/patients/', PatientListView.as_view(), name='list_patients'),
    path('staff/upload-record/', UploadMedicalRecordView.as_view(), name='upload_record'),
    path('staff/patients/<int:patient_id>/records/', PatientRecordsView.as_view(), name='patient_records'),
    
    # PATIENT APPROVAL endpoints
    path('staff/patients/pending/', PendingPatientsView.as_view(), name='pending_patients'),
    path('staff/patients/<int:patient_id>/approve/', ApprovePatientView.as_view(), name='approve_patient'),
    path('staff/patients/<int:patient_id>/reject/', RejectPatientView.as_view(), name='reject_patient'),
    
    # MEDICAL RECORD EDITING/APPROVAL endpoints
    path('staff/records/pending/', PendingRecordsView.as_view(), name='pending_records'),
    path('staff/records/<int:pk>/edit/', EditMedicalRecordView.as_view(), name='edit_record'),
    path('staff/records/<int:record_id>/approve/', ApproveMedicalRecordView.as_view(), name='approve_record'),
    path('staff/records/<int:record_id>/reject/', RejectMedicalRecordView.as_view(), name='reject_record'),
    
    # SHARED endpoints (Staff, Admin, Patient - permissions handled in view)
    path('records/<int:record_id>/download/', DownloadMedicalRecordView.as_view(), name='download_record'),
    
    # PATIENT endpoints
    path('patient/my-records/', MyMedicalRecordsView.as_view(), name='my_records'),
    path('patient/my-records/<int:pk>/', MyMedicalRecordDetailView.as_view(), name='my_record_detail'),
    path('patient/my-records/<int:record_id>/verify/', VerifyMyRecordView.as_view(), name='verify_my_record'),
    
    # ADMIN endpoints
    path('admin/system-stats/', SystemStatsView.as_view(), name='system_stats'),
    path('admin/audit-logs/', AuditLogView.as_view(), name='audit_logs'),
    path('admin/activity/', SystemActivityView.as_view(), name='system_activity'),
    path('admin/users/<int:user_id>/activity/', UserActivityView.as_view(), name='user_activity'),
]