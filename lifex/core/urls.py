from django.urls import path
from .views import (
    PatientListView,
    PatientDocumentUploadView,
    PatientDocumentListView,
    PatientDocumentDetailView,
)

app_name = 'core'

urlpatterns = [
    # Patient management
    path('patients/', PatientListView.as_view(), name='patient_list'),
    
    # Document management
    path('patients/<int:patient_id>/documents/', PatientDocumentListView.as_view(), name='patient_documents'),
    path('patients/<int:patient_id>/upload/', PatientDocumentUploadView.as_view(), name='upload_document'),
    path('documents/<int:pk>/', PatientDocumentDetailView.as_view(), name='document_detail'),
]