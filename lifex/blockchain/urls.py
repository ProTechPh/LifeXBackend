from django.urls import path
from .medical_views import (
    RegisterPatientView,
    ListPatientsView,
    UploadMedicalRecordView,
    PatientRecordsView,
    MyMedicalRecordsView,
    MyMedicalRecordDetailView,
    VerifyMyRecordView,
    PendingPatientsView,
    ApproveRejectPatientView,
    SystemStatsView,
)

app_name = 'blockchain'

urlpatterns = [
    # IT STAFF endpoints
    path('staff/register-patient/', RegisterPatientView.as_view(), name='register_patient'),
    path('staff/patients/', ListPatientsView.as_view(), name='list_patients'),
    path('staff/upload-record/', UploadMedicalRecordView.as_view(), name='upload_record'),
    path('staff/patient/<int:patient_id>/records/', PatientRecordsView.as_view(), name='patient_records'),
    
    # PATIENT endpoints
    path('patient/my-records/', MyMedicalRecordsView.as_view(), name='my_records'),
    path('patient/my-records/<int:pk>/', MyMedicalRecordDetailView.as_view(), name='my_record_detail'),
    path('patient/my-records/<int:record_id>/verify/', VerifyMyRecordView.as_view(), name='verify_my_record'),
    
    # ADMIN endpoints
    path('admin/pending-patients/', PendingPatientsView.as_view(), name='pending_patients'),
    path('admin/patient/<int:patient_id>/approve-reject/', ApproveRejectPatientView.as_view(), name='approve_reject_patient'),
    path('admin/system-stats/', SystemStatsView.as_view(), name='system_stats'),
]