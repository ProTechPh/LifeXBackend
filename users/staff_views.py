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
