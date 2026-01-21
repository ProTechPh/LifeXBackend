from django.contrib.auth import get_user_model
User = get_user_model()

# Create Admin
admin = User.objects.create_superuser(
    email='admin@hospital.com',
    password='admin123',
    first_name='Admin',
    last_name='User'
)
print(f"✅ Admin created: {admin.email}")

# Create IT Staff
it_staff = User.objects.create_user(
    email='itstaff@hospital.com',
    password='itstaff123',
    first_name='IT',
    last_name='Staff',
    role='IT_STAFF',
    account_status='APPROVED'
)
it_staff.is_staff = True  # For Django admin access
it_staff.save()
print(f"✅ IT Staff created: {it_staff.email}")

# Create Test Patient (Approved)
patient1 = User.objects.create_user(
    email='patient1@email.com',
    password='patient123',
    first_name='John',
    last_name='Doe',
    role='PATIENT',
    account_status='APPROVED'
)
print(f"✅ Patient 1 created: {patient1.email}")

# Create Test Patient (Pending)
patient2 = User.objects.create_user(
    email='patient2@email.com',
    password='patient123',
    first_name='Jane',
    last_name='Smith',
    role='PATIENT',
    account_status='PENDING'
)
print(f"✅ Patient 2 created: {patient2.email}")