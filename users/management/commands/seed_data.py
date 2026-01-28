from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from users.models import User, Department, DoctorSchedule
import random


class Command(BaseCommand):
    help = 'Seeds the database with test users for all roles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            User.objects.all().delete()
            Department.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Data cleared!'))

        self.stdout.write(self.style.SUCCESS('Starting database seeding...'))

        # Create Departments
        departments_data = [
            {'name': 'Cardiology', 'code': 'CARD', 'description': 'Heart and cardiovascular system'},
            {'name': 'Neurology', 'code': 'NEUR', 'description': 'Brain and nervous system'},
            {'name': 'Orthopedics', 'code': 'ORTH', 'description': 'Bones, joints, and muscles'},
            {'name': 'Pediatrics', 'code': 'PEDI', 'description': 'Children\'s health'},
            {'name': 'Radiology', 'code': 'RADI', 'description': 'Medical imaging'},
            {'name': 'Emergency', 'code': 'EMER', 'description': 'Emergency care'},
            {'name': 'General Medicine', 'code': 'GENM', 'description': 'General medical care'},
        ]

        departments = {}
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults={
                    'name': dept_data['name'],
                    'description': dept_data['description']
                }
            )
            departments[dept_data['code']] = dept
            if created:
                self.stdout.write(f'  Created department: {dept.name}')

        # Create Admin Users
        admin_users = [
            {
                'email': 'admin@lifex.com',
                'password': 'admin123',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
                'account_status': 'APPROVED',
            },
            {
                'email': 'admin2@lifex.com',
                'password': 'admin123',
                'first_name': 'Maria',
                'last_name': 'Santos',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
                'account_status': 'APPROVED',
                'phone_number': '+63 917 123 4567',
            },
        ]

        for user_data in admin_users:
            password = user_data.pop('password')
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'  Created admin: {user.email}')

        # Create Receptionist Users
        receptionist_users = [
            {
                'email': 'receptionist1@lifex.com',
                'password': 'recep123',
                'first_name': 'Ana',
                'last_name': 'Cruz',
                'role': 'RECEPTIONIST',
                'department': departments['GENM'],
                'employee_id': 'REC001',
                'phone_number': '+63 917 234 5678',
                'account_status': 'APPROVED',
            },
            {
                'email': 'receptionist2@lifex.com',
                'password': 'recep123',
                'first_name': 'Rosa',
                'last_name': 'Reyes',
                'role': 'RECEPTIONIST',
                'department': departments['EMER'],
                'employee_id': 'REC002',
                'phone_number': '+63 917 345 6789',
                'account_status': 'APPROVED',
            },
        ]

        for user_data in receptionist_users:
            password = user_data.pop('password')
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'  Created receptionist: {user.email}')

        # Create Nurse Users
        nurse_users = [
            {
                'email': 'nurse1@lifex.com',
                'password': 'nurse123',
                'first_name': 'Elena',
                'last_name': 'Garcia',
                'role': 'NURSE',
                'department': departments['CARD'],
                'employee_id': 'NUR001',
                'license_number': 'RN-123456',
                'phone_number': '+63 917 456 7890',
                'account_status': 'APPROVED',
            },
            {
                'email': 'nurse2@lifex.com',
                'password': 'nurse123',
                'first_name': 'Carmen',
                'last_name': 'Mendoza',
                'role': 'NURSE',
                'department': departments['PEDI'],
                'employee_id': 'NUR002',
                'license_number': 'RN-234567',
                'phone_number': '+63 917 567 8901',
                'account_status': 'APPROVED',
            },
            {
                'email': 'nurse3@lifex.com',
                'password': 'nurse123',
                'first_name': 'Isabel',
                'last_name': 'Torres',
                'role': 'NURSE',
                'department': departments['EMER'],
                'employee_id': 'NUR003',
                'license_number': 'RN-345678',
                'phone_number': '+63 917 678 9012',
                'account_status': 'APPROVED',
            },
        ]

        for user_data in nurse_users:
            password = user_data.pop('password')
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'  Created nurse: {user.email}')

        # Create Doctor Users
        doctor_users = [
            {
                'email': 'doctor1@lifex.com',
                'password': 'doctor123',
                'first_name': 'Juan',
                'last_name': 'Dela Cruz',
                'role': 'DOCTOR',
                'department': departments['CARD'],
                'employee_id': 'DOC001',
                'license_number': 'MD-123456',
                'specialization': 'Cardiology',
                'phone_number': '+63 917 789 0123',
                'account_status': 'APPROVED',
            },
            {
                'email': 'doctor2@lifex.com',
                'password': 'doctor123',
                'first_name': 'Maria',
                'last_name': 'Gonzales',
                'role': 'DOCTOR',
                'department': departments['NEUR'],
                'employee_id': 'DOC002',
                'license_number': 'MD-234567',
                'specialization': 'Neurology',
                'phone_number': '+63 917 890 1234',
                'account_status': 'APPROVED',
            },
            {
                'email': 'doctor3@lifex.com',
                'password': 'doctor123',
                'first_name': 'Pedro',
                'last_name': 'Ramos',
                'role': 'DOCTOR',
                'department': departments['ORTH'],
                'employee_id': 'DOC003',
                'license_number': 'MD-345678',
                'specialization': 'Orthopedics',
                'phone_number': '+63 917 901 2345',
                'account_status': 'APPROVED',
            },
            {
                'email': 'doctor4@lifex.com',
                'password': 'doctor123',
                'first_name': 'Sofia',
                'last_name': 'Aquino',
                'role': 'DOCTOR',
                'department': departments['PEDI'],
                'employee_id': 'DOC004',
                'license_number': 'MD-456789',
                'specialization': 'Pediatrics',
                'phone_number': '+63 917 012 3456',
                'account_status': 'APPROVED',
            },
            {
                'email': 'doctor5@lifex.com',
                'password': 'doctor123',
                'first_name': 'Ricardo',
                'last_name': 'Bautista',
                'role': 'DOCTOR',
                'department': departments['GENM'],
                'employee_id': 'DOC005',
                'license_number': 'MD-567890',
                'specialization': 'General Medicine',
                'phone_number': '+63 917 123 4560',
                'account_status': 'APPROVED',
            },
        ]

        doctors = []
        for user_data in doctor_users:
            password = user_data.pop('password')
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data
            )
            if created:
                user.set_password(password)
                user.save()
                doctors.append(user)
                self.stdout.write(f'  Created doctor: {user.email}')

        # Create Doctor Schedules
        self.stdout.write('Creating doctor schedules...')
        for doctor in doctors:
            # Create schedules for weekdays (Monday to Friday)
            for day in range(5):
                schedule, created = DoctorSchedule.objects.get_or_create(
                    doctor=doctor,
                    day_of_week=day,
                    defaults={
                        'start_time': '09:00',
                        'end_time': '17:00',
                        'slot_duration_minutes': 30,
                        'max_patients_per_slot': 1,
                        'is_active': True,
                    }
                )
                if created:
                    self.stdout.write(f'    Created schedule for {doctor.get_full_name()} on {schedule.get_day_of_week_display()}')

        # Create Patient Users
        patient_users = [
            {
                'email': 'patient1@lifex.com',
                'password': 'patient123',
                'first_name': 'Jose',
                'last_name': 'Rizal',
                'role': 'PATIENT',
                'date_of_birth': date(1990, 6, 19),
                'gender': 'MALE',
                'phone_number': '+63 917 111 2222',
                'address_line1': '123 Rizal Street',
                'city': 'Manila',
                'state_province': 'Metro Manila',
                'postal_code': '1000',
                'country': 'Philippines',
                'account_status': 'APPROVED',
                'kyc_status': 'VERIFIED',
                'emergency_contact_name': 'Maria Rizal',
                'emergency_contact_phone': '+63 917 222 3333',
                'emergency_contact_relationship': 'Spouse',
            },
            {
                'email': 'patient2@lifex.com',
                'password': 'patient123',
                'first_name': 'Andres',
                'last_name': 'Bonifacio',
                'role': 'PATIENT',
                'date_of_birth': date(1985, 11, 30),
                'gender': 'MALE',
                'phone_number': '+63 917 333 4444',
                'address_line1': '456 Bonifacio Avenue',
                'city': 'Quezon City',
                'state_province': 'Metro Manila',
                'postal_code': '1100',
                'country': 'Philippines',
                'account_status': 'APPROVED',
                'kyc_status': 'VERIFIED',
                'emergency_contact_name': 'Gregoria Bonifacio',
                'emergency_contact_phone': '+63 917 444 5555',
                'emergency_contact_relationship': 'Spouse',
            },
            {
                'email': 'patient3@lifex.com',
                'password': 'patient123',
                'first_name': 'Gabriela',
                'last_name': 'Silang',
                'role': 'PATIENT',
                'date_of_birth': date(1995, 3, 19),
                'gender': 'FEMALE',
                'phone_number': '+63 917 555 6666',
                'address_line1': '789 Silang Road',
                'city': 'Makati',
                'state_province': 'Metro Manila',
                'postal_code': '1200',
                'country': 'Philippines',
                'account_status': 'APPROVED',
                'kyc_status': 'VERIFIED',
                'emergency_contact_name': 'Diego Silang',
                'emergency_contact_phone': '+63 917 666 7777',
                'emergency_contact_relationship': 'Spouse',
            },
            {
                'email': 'patient4@lifex.com',
                'password': 'patient123',
                'first_name': 'Emilio',
                'last_name': 'Aguinaldo',
                'role': 'PATIENT',
                'date_of_birth': date(1988, 3, 22),
                'gender': 'MALE',
                'phone_number': '+63 917 777 8888',
                'address_line1': '321 Aguinaldo Highway',
                'city': 'Cavite',
                'state_province': 'Cavite',
                'postal_code': '4100',
                'country': 'Philippines',
                'account_status': 'APPROVED',
                'kyc_status': 'PENDING',
            },
            {
                'email': 'patient5@lifex.com',
                'password': 'patient123',
                'first_name': 'Melchora',
                'last_name': 'Aquino',
                'role': 'PATIENT',
                'date_of_birth': date(1992, 1, 6),
                'gender': 'FEMALE',
                'phone_number': '+63 917 888 9999',
                'address_line1': '654 Tandang Sora Avenue',
                'city': 'Quezon City',
                'state_province': 'Metro Manila',
                'postal_code': '1116',
                'country': 'Philippines',
                'account_status': 'PENDING',
                'kyc_status': 'NOT_STARTED',
            },
        ]

        for user_data in patient_users:
            password = user_data.pop('password')
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'  Created patient: {user.email}')

        self.stdout.write(self.style.SUCCESS('\n=== Database seeding completed! ===\n'))
        self.stdout.write(self.style.SUCCESS('Login credentials:'))
        self.stdout.write('  Admin: admin@lifex.com / admin123')
        self.stdout.write('  Receptionist: receptionist1@lifex.com / recep123')
        self.stdout.write('  Nurse: nurse1@lifex.com / nurse123')
        self.stdout.write('  Doctor: doctor1@lifex.com / doctor123')
        self.stdout.write('  Patient: patient1@lifex.com / patient123')
        self.stdout.write('\nAll users follow the pattern: [role][number]@lifex.com / [role]123')
