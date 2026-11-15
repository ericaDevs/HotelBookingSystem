from django.shortcuts import render


def staff_login(request):
    return render(request, 'staff_auth/login.html')


def staff_dashboard(request):
    return render(request, 'staff_portal/overview.html')
