from django.shortcuts import render

def login_view(request):
    """Login page"""
    return render(request, 'login.html')

def it_staff_dashboard(request):
    """IT Staff dashboard"""
    return render(request, 'it_staff_dashboard.html')

def patient_portal(request):
    """Patient portal"""
    return render(request, 'patient_portal.html')

def admin_dashboard(request):
    """Admin dashboard"""
    return render(request, 'admin_dashboard.html')