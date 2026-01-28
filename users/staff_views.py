from rest_framework import status, generics, filters, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import Department, DoctorSchedule, Appointment, Notification, DoctorNurseAssignment
from .serializers import (
    DepartmentSerializer, 
    DoctorScheduleSerializer, 
    AppointmentSerializer, 
    NotificationSerializer,
    UserSerializer
)
from .permissions import IsReceptionist, IsDoctor, IsNurse, CanViewDoctorSchedule, CanManageAppointments

User = get_user_model()

@extend_schema(
    tags=['Hospital Structure'],
    summary='List departments',
    description='Get a list of all active hospital departments'
)
class DepartmentListView(generics.ListAPIView):
    """List all hospital departments"""
    queryset = Department.objects.filter(is_active=True)
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

@extend_schema(
    tags=['Hospital Structure'],
    summary='List doctors by department',
    description='Get a list of all active doctors in a specific department (Receptionist only)',
    parameters=[
        OpenApiParameter(
            name='dept_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Department ID'
        ),
    ]
)
class DoctorByDepartmentListView(generics.ListAPIView):
    """List all doctors in a specific department (For Receptionists)"""
    serializer_class = UserSerializer
    permission_classes = [IsReceptionist]
    
    def get_queryset(self):
        dept_id = self.kwargs.get('dept_id')
        return User.objects.filter(role='DOCTOR', department_id=dept_id, is_active=True)

@extend_schema(
    tags=['Scheduling'],
    summary='Get doctor schedule',
    description='View schedule for a specific doctor',
    parameters=[
        OpenApiParameter(
            name='doctor_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Doctor ID'
        ),
    ]
)
class DoctorScheduleListView(generics.ListAPIView):
    """View schedule for a specific doctor"""
    serializer_class = DoctorScheduleSerializer
    permission_classes = [CanViewDoctorSchedule]
    
    def get_queryset(self):
        doctor_id = self.kwargs.get('doctor_id')
        return DoctorSchedule.objects.filter(doctor_id=doctor_id, is_active=True)

@extend_schema(
    tags=['Appointments'],
    summary='Create appointment',
    description='Create a new appointment (Receptionists only). Automatically notifies the assigned doctor.',
    examples=[
        OpenApiExample(
            'Create Appointment',
            value={
                'patient': 1,
                'doctor': 2,
                'appointment_date': '2024-02-15',
                'appointment_time': '14:30:00',
                'appointment_type': 'GENERAL',
                'reason': 'Regular checkup'
            }
        )
    ]
)
class AppointmentCreateView(generics.CreateAPIView):
    """Create a new appointment (Receptionists only)"""
    serializer_class = AppointmentSerializer
    permission_classes = [IsReceptionist]
    
    def perform_create(self, serializer):
        appointment = serializer.save(booked_by=self.request.user)
        
        # Notify the doctor
        Notification.objects.create(
            recipient=appointment.doctor,
            notification_type='NEW_APPOINTMENT',
            priority='NORMAL',
            title='New Appointment Scheduled',
            message=f'New appointment scheduled for {appointment.patient.get_full_name()} on {appointment.appointment_date} at {appointment.appointment_time}.',
            related_appointment=appointment
        )

class AppointmentListView(generics.ListAPIView):
    """List appointments
    - Receptionists see all
    - Doctors see their own
    - Patients see their own
    """
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageAppointments]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['patient__email', 'patient__first_name', 'patient__last_name']
    ordering_fields = ['appointment_date', 'appointment_time']
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['RECEPTIONIST', 'ADMIN', 'NURSE']:
            return Appointment.objects.all()
        elif user.role == 'DOCTOR':
            return Appointment.objects.filter(doctor=user)
        elif user.role == 'PATIENT':
            return Appointment.objects.filter(patient=user)
        return Appointment.objects.none()

class CheckInPatientView(APIView):
    """Check in a patient for their appointment and notify the doctor"""
    permission_classes = [IsReceptionist]
    
    def post(self, request, appointment_id):
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            appointment.status = 'CHECKED_IN'
            appointment.checked_in_at = timezone.now()
            appointment.save()
            
            # Notify the doctor with URGENT priority
            Notification.objects.create(
                recipient=appointment.doctor,
                notification_type='PATIENT_CHECK_IN',
                priority='HIGH',
                title='Patient Arrived',
                message=f'Patient {appointment.patient.get_full_name()} has checked in and is waiting for their appointment.',
                related_appointment=appointment
            )
            
            return Response({'message': 'Patient checked in successfully. Doctor has been notified.'}, status=status.HTTP_200_OK)
        except Appointment.DoesNotExist:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

class CompleteAppointmentView(APIView):
    """Doctors can complete an appointment"""
    permission_classes = [IsDoctor]
    
    def post(self, request, appointment_id):
        try:
            appointment = Appointment.objects.get(id=appointment_id, doctor=request.user)
            appointment.status = 'COMPLETED'
            appointment.completed_at = timezone.now()
            
            # Get notes from request if provided
            notes = request.data.get('notes', '')
            if notes:
                appointment.notes = notes
            
            appointment.save()
            
            serializer = AppointmentSerializer(appointment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Appointment.DoesNotExist:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

class CancelAppointmentView(APIView):
    """Cancel an appointment (Receptionist or Patient)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, appointment_id):
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            
            # Check permissions: Receptionist can cancel any, Patient can cancel their own
            if request.user.role not in ['RECEPTIONIST', 'ADMIN']:
                if request.user.role == 'PATIENT' and appointment.patient != request.user:
                    return Response({'error': 'You can only cancel your own appointments'}, status=status.HTTP_403_FORBIDDEN)
                elif request.user.role not in ['PATIENT']:
                    return Response({'error': 'You do not have permission to cancel appointments'}, status=status.HTTP_403_FORBIDDEN)
            
            appointment.status = 'CANCELLED'
            
            # Get cancellation reason from request if provided
            reason = request.data.get('reason', '')
            if reason:
                appointment.notes = f"Cancelled: {reason}"
            
            appointment.save()
            
            # Notify the doctor
            if appointment.doctor:
                Notification.objects.create(
                    recipient=appointment.doctor,
                    notification_type='APPOINTMENT_CANCELLED',
                    priority='NORMAL',
                    title='Appointment Cancelled',
                    message=f'Appointment with {appointment.patient.get_full_name()} on {appointment.appointment_date} at {appointment.appointment_time} has been cancelled.',
                    related_appointment=appointment
                )
            
            serializer = AppointmentSerializer(appointment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Appointment.DoesNotExist:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

class UpdateAppointmentView(generics.UpdateAPIView):
    """Update an appointment (Receptionist only)"""
    serializer_class = AppointmentSerializer
    permission_classes = [IsReceptionist]
    queryset = Appointment.objects.all()
    lookup_field = 'pk'
    
    def perform_update(self, serializer):
        appointment = serializer.save()
        
        # Notify the doctor about the update
        if appointment.doctor:
            Notification.objects.create(
                recipient=appointment.doctor,
                notification_type='APPOINTMENT_UPDATED',
                priority='NORMAL',
                title='Appointment Updated',
                message=f'Appointment with {appointment.patient.get_full_name()} has been updated. New date: {appointment.appointment_date} at {appointment.appointment_time}.',
                related_appointment=appointment
            )

class NotificationListView(generics.ListAPIView):
    """List notifications for the logged in user (Primarily for Doctors)"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

class NotificationMarkReadView(APIView):
    """Mark a notification as read"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, recipient=request.user)
            notification.mark_as_read()
            return Response({'message': 'Notification marked as read'}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

class NotificationMarkAllReadView(APIView):
    """Mark all notifications as read for the current user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return Response({
            'message': f'{updated_count} notifications marked as read',
            'count': updated_count
        }, status=status.HTTP_200_OK)

class NotificationDeleteView(APIView):
    """Delete a notification"""
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, recipient=request.user)
            notification.delete()
            return Response({'message': 'Notification deleted successfully'}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

class NotificationStatsView(APIView):
    """Get notification statistics for the current user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user_notifications = Notification.objects.filter(recipient=request.user)
        
        stats = {
            'total': user_notifications.count(),
            'unread': user_notifications.filter(is_read=False).count(),
            'read': user_notifications.filter(is_read=True).count(),
            'by_priority': {
                'urgent': user_notifications.filter(priority='URGENT').count(),
                'high': user_notifications.filter(priority='HIGH').count(),
                'normal': user_notifications.filter(priority='NORMAL').count(),
                'low': user_notifications.filter(priority='LOW').count(),
            },
            'by_type': {}
        }
        
        # Count by notification type
        for notif_type in ['NEW_APPOINTMENT', 'APPOINTMENT_CANCELLED', 'APPOINTMENT_UPDATED', 
                          'PATIENT_CHECK_IN', 'RECORD_UPLOADED', 'SYSTEM_ALERT']:
            stats['by_type'][notif_type.lower()] = user_notifications.filter(
                notification_type=notif_type
            ).count()
        
        return Response(stats, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Dashboard'],
    summary='Get doctor dashboard statistics',
    description='Get statistics for doctor dashboard including patient count, appointments, etc.'
)
class DoctorDashboardStatsView(APIView):
    """Get dashboard statistics for doctors"""
    permission_classes = [IsDoctor]
    
    def get(self, request):
        from blockchain.models import MedicalRecord
        from datetime import date
        
        doctor = request.user
        
        # Get all patients who have appointments with this doctor
        patient_ids = Appointment.objects.filter(doctor=doctor).values_list('patient_id', flat=True).distinct()
        total_patients = patient_ids.count()
        
        # Get today's appointments
        today = date.today()
        todays_appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=today,
            status__in=['SCHEDULED', 'CHECKED_IN', 'IN_PROGRESS']
        ).count()
        
        # Get pending medical records that need review (uploaded by this doctor but not verified)
        pending_reviews = MedicalRecord.objects.filter(
            uploaded_by=doctor,
            approval_status='PENDING'
        ).count()
        
        # Get recent lab results (last 7 days)
        from datetime import timedelta
        week_ago = today - timedelta(days=7)
        recent_lab_results = MedicalRecord.objects.filter(
            patient_id__in=patient_ids,
            record_type='LAB_RESULT',
            date_of_service__gte=week_ago
        ).count()
        
        # Get upcoming appointments (next 5)
        upcoming_appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date__gte=today,
            status__in=['SCHEDULED', 'CHECKED_IN']
        ).order_by('appointment_date', 'appointment_time')[:5]
        
        upcoming_list = []
        for apt in upcoming_appointments:
            upcoming_list.append({
                'id': apt.id,
                'patient_name': apt.patient.get_full_name(),
                'appointment_date': apt.appointment_date,
                'appointment_time': apt.appointment_time,
                'reason': apt.reason,
                'status': apt.status
            })
        
        stats = {
            'total_patients': total_patients,
            'todays_appointments': todays_appointments,
            'pending_reviews': pending_reviews,
            'recent_lab_results': recent_lab_results,
            'upcoming_appointments': upcoming_list
        }
        
        return Response(stats, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Dashboard'],
    summary='Get admin system statistics',
    description='Get comprehensive system statistics for admin dashboard'
)
class AdminSystemStatsView(APIView):
    """Get system statistics for admin dashboard"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        from blockchain.models import MedicalRecord, BlockchainTransaction
        from datetime import date, timedelta
        
        # User statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_patients = User.objects.filter(role='PATIENT').count()
        total_staff = User.objects.filter(role__in=['DOCTOR', 'NURSE', 'RECEPTIONIST', 'ADMIN']).count()
        total_doctors = User.objects.filter(role='DOCTOR').count()
        total_nurses = User.objects.filter(role='NURSE').count()
        total_receptionists = User.objects.filter(role='RECEPTIONIST').count()
        
        # Medical records statistics
        total_medical_records = MedicalRecord.objects.count()
        verified_records = MedicalRecord.objects.filter(is_verified=True).count()
        
        # Appointment statistics
        total_appointments = Appointment.objects.count()
        today = date.today()
        todays_appointments = Appointment.objects.filter(appointment_date=today).count()
        
        # Blockchain statistics
        total_blockchain_transactions = BlockchainTransaction.objects.count()
        successful_transactions = BlockchainTransaction.objects.filter(status='SUCCESS').count()
        failed_transactions = BlockchainTransaction.objects.filter(status='FAILED').count()
        
        # Recent activities (last 10)
        recent_activities = []
        
        # Get recent user registrations
        recent_users = User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=7)
        ).order_by('-date_joined')[:5]
        
        for user in recent_users:
            time_diff = timezone.now() - user.date_joined
            if time_diff.days > 0:
                time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
            elif time_diff.seconds // 3600 > 0:
                hours = time_diff.seconds // 3600
                time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                minutes = time_diff.seconds // 60
                time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            
            recent_activities.append({
                'type': 'user_registration',
                'icon': 'Users',
                'message': f"New user registered: {user.get_full_name()} ({user.role})",
                'time': time_ago,
                'timestamp': user.date_joined.isoformat()
            })
        
        # Get recent appointments
        recent_appointments = Appointment.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=1)
        ).order_by('-created_at')[:3]
        
        for apt in recent_appointments:
            time_diff = timezone.now() - apt.created_at
            if time_diff.seconds // 3600 > 0:
                hours = time_diff.seconds // 3600
                time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                minutes = time_diff.seconds // 60
                time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            
            recent_activities.append({
                'type': 'appointment',
                'icon': 'Calendar',
                'message': f"New appointment: {apt.patient.get_full_name()} with Dr. {apt.doctor.get_full_name()}",
                'time': time_ago,
                'timestamp': apt.created_at.isoformat()
            })
        
        # Sort activities by timestamp
        recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_activities = recent_activities[:10]
        
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'total_patients': total_patients,
            'total_staff': total_staff,
            'total_doctors': total_doctors,
            'total_nurses': total_nurses,
            'total_receptionists': total_receptionists,
            'total_medical_records': total_medical_records,
            'verified_records': verified_records,
            'total_appointments': total_appointments,
            'todays_appointments': todays_appointments,
            'total_blockchain_transactions': total_blockchain_transactions,
            'successful_transactions': successful_transactions,
            'failed_transactions': failed_transactions,
            'recent_activities': recent_activities,
            'system_health': 'Good' if failed_transactions == 0 else 'Degraded'
        }
        
        return Response(stats, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Dashboard'],
    summary='Get nurse dashboard statistics',
    description='Get statistics for nurse dashboard including records uploaded, pending approvals, etc.'
)
class NurseDashboardStatsView(APIView):
    """Get dashboard statistics for nurses"""
    permission_classes = [IsNurse]
    
    def get(self, request):
        from blockchain.models import MedicalRecord
        from datetime import date, timedelta
        
        nurse = request.user
        today = date.today()
        
        # Get records uploaded today by this nurse
        records_uploaded_today = MedicalRecord.objects.filter(
            uploaded_by=nurse,
            created_at__date=today
        ).count()
        
        # Get pending approvals (records that need approval)
        pending_approvals = MedicalRecord.objects.filter(
            approval_status='PENDING'
        ).count()
        
        # Get patients assigned to this nurse (through doctor assignments)
        from .models import DoctorNurseAssignment
        assigned_doctors = DoctorNurseAssignment.objects.filter(
            nurse=nurse
        ).values_list('doctor_id', flat=True)
        
        # Get unique patients who have appointments with assigned doctors
        patients_assigned = Appointment.objects.filter(
            doctor_id__in=assigned_doctors
        ).values_list('patient_id', flat=True).distinct().count()
        
        # Get total records processed by this nurse (this month)
        month_start = today.replace(day=1)
        records_processed = MedicalRecord.objects.filter(
            uploaded_by=nurse,
            created_at__gte=month_start
        ).count()
        
        # Get pending records for approval
        pending_records_list = MedicalRecord.objects.filter(
            approval_status='PENDING'
        ).select_related('patient', 'uploaded_by').order_by('-created_at')[:10]
        
        pending_records = []
        for record in pending_records_list:
            pending_records.append({
                'id': record.id,
                'patient_name': record.patient.get_full_name(),
                'record_type': record.record_type,
                'uploaded_by': record.uploaded_by.get_full_name() if record.uploaded_by else 'External',
                'upload_date': record.created_at.isoformat(),
                'status': record.approval_status.lower()
            })
        
        stats = {
            'records_uploaded_today': records_uploaded_today,
            'pending_approvals': pending_approvals,
            'patients_assigned': patients_assigned,
            'records_processed': records_processed,
            'pending_records': pending_records
        }
        
        return Response(stats, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Dashboard'],
    summary='Get receptionist dashboard statistics',
    description='Get statistics for receptionist dashboard including registrations, appointments, etc.'
)
class ReceptionistDashboardStatsView(APIView):
    """Get dashboard statistics for receptionists"""
    permission_classes = [IsReceptionist]
    
    def get(self, request):
        from datetime import date
        
        today = date.today()
        
        # Get patients registered today
        patients_registered_today = User.objects.filter(
            role='PATIENT',
            date_joined__date=today
        ).count()
        
        # Get appointments scheduled for today
        appointments_scheduled = Appointment.objects.filter(
            appointment_date=today
        ).count()
        
        # Get pending appointments (scheduled but not checked in)
        pending_appointments = Appointment.objects.filter(
            appointment_date=today,
            status='SCHEDULED'
        ).count()
        
        # Get checked-in patients today
        checked_in_patients = Appointment.objects.filter(
            appointment_date=today,
            status__in=['CHECKED_IN', 'IN_PROGRESS']
        ).count()
        
        # Get today's appointments with details
        todays_appointments = Appointment.objects.filter(
            appointment_date=today
        ).select_related('patient', 'doctor').order_by('appointment_time')[:10]
        
        appointments_list = []
        for apt in todays_appointments:
            appointments_list.append({
                'id': apt.id,
                'patient_name': apt.patient.get_full_name(),
                'doctor_name': apt.doctor.get_full_name(),
                'appointment_time': apt.appointment_time.strftime('%H:%M'),
                'appointment_type': apt.appointment_type,
                'status': apt.status,
                'reason': apt.reason
            })
        
        stats = {
            'patients_registered_today': patients_registered_today,
            'appointments_scheduled': appointments_scheduled,
            'pending_appointments': pending_appointments,
            'checked_in_patients': checked_in_patients,
            'todays_appointments': appointments_list
        }
        
        return Response(stats, status=status.HTTP_200_OK)
